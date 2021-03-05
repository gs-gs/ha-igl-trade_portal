"""
Things related to the CoO packaging and sending to the upstream
"""
import base64
import datetime
import json
import logging
import mimetypes

# TODO: replace to pyca/cryptography as Bandit advises (low)
from Crypto.Cipher import AES

import requests
from constance import config
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.urls import reverse
from django.utils import timezone

from intergov_client.predicates import Predicates

from trade_portal.documents.models import (
    Document,
    DocumentHistoryItem,
    NodeMessage,
    OaDetails,
)
from trade_portal.documents.services import BaseIgService
from trade_portal.documents.services.notarize import NotaryService

logger = logging.getLogger(__name__)


class AESCipher:
    BS = 256 // 8

    def __init__(self, key):
        self.key = bytes.fromhex(key)

    def pad(self, s):
        return s + (self.BS - len(s) % self.BS) * chr(self.BS - len(s) % self.BS)

    def unpad(self, s):
        return s[: -ord(s[len(s) - 1 :])]

    def encrypt_with_params_separate(self, raw):
        encoded = base64.b64encode(raw.encode("utf-8"))
        cipher = AES.new(self.key, AES.MODE_GCM)
        ciphertext, tag = cipher.encrypt_and_digest(encoded)
        return (
            base64.b64encode(cipher.nonce).decode("utf-8"),
            base64.b64encode(tag).decode("utf-8"),
            base64.b64encode(ciphertext).decode("utf-8"),
        )

    def decrypt(self, iv, tag, ciphertext):
        iv = base64.b64decode(iv)
        tag = base64.b64decode(tag)
        ciphertext = base64.b64decode(ciphertext)
        cipher = AES.new(self.key, AES.MODE_GCM, iv)
        return cipher.decrypt_and_verify(ciphertext, tag)


class OAClient:
    """
    Client working with our OA wrap API, moved out for easy mocking in tests,
    code separation and possible replacement by native code
    """

    def wrap_document(self, oa_doc):
        if getattr(settings, "IS_UNITTEST", False) is True:
            raise EnvironmentError("This procedure must not be called from unittest")
        return requests.post(
            settings.OA_WRAP_API_URL + "/document/wrap",
            json={
                "document": oa_doc,
                "params": {
                    "version": "https://schema.openattestation.com/2.0/schema.json",
                },
            },
        )


class DocumentService(BaseIgService):
    def __init__(self, oa_client=None, *args, **kwargs):
        if not oa_client:
            oa_client = OAClient()
        self.oa_client = oa_client
        super().__init__(*args, **kwargs)

    def issue(self, document: Document) -> bool:
        """
        Does all issue/OA notarize/IGL message sending work
        This procedure is a good candidate for refactoring to smaller clients, services and functions
        """
        from trade_portal.documents.tasks import document_oa_verify

        document.verification_status = Document.V_STATUS_PENDING
        document.status = Document.STATUS_NOT_SENT
        document.save()

        subject = "{}.{}.{}".format(
            settings.ICL_APP_COUNTRY.upper(),
            (document.created_by_org.business_id).replace(".", "-"),
            document.short_id,
        )

        # step 2. Render the OAv2 doc with attachments
        oa_doc = self._render_oa_v2_document(document, subject)
        # step 2. Append EDI3 document, merging it to the root level
        oa_doc.update(document.get_rendered_edi3_document())

        DocumentHistoryItem.objects.create(
            type="text",
            document=document,
            message=f"OA document has been generated, size: {len(json.dumps(oa_doc))}b",
            related_file=default_storage.save(
                f"incoming/{document.id}/oa-doc.json",
                ContentFile(json.dumps(oa_doc, indent=2).encode("utf-8")),
            ),
        )

        # step 3, slow: wrap OA document using external api for wrapping documents
        # TODO: think about replacing by native solution (won't give much performance increase)
        try:
            oa_doc_wrapped_resp = self.oa_client.wrap_document(oa_doc)
            if oa_doc_wrapped_resp.status_code != 200:
                # this is not common to have API answering non-200
                logger.warning("Received %s for oa doc wrap step", oa_doc_wrapped_resp)
                raise Exception(oa_doc_wrapped_resp.json())
            else:
                # OA document is wrapped correctly
                oa_doc_wrapped = oa_doc_wrapped_resp.json()
                wrapped_doc_merkle_root = oa_doc_wrapped.get("signature", {}).get("merkleRoot")
                if not wrapped_doc_merkle_root:
                    raise Exception("Empty merkleRoot for " + oa_doc_wrapped_resp.content.decode("utf-8"))
                DocumentHistoryItem.objects.create(
                    type="text",
                    document=document,
                    message=f"OA document has been wrapped, new size: {len(oa_doc_wrapped_resp.content)}b",
                    related_file=default_storage.save(
                        f"incoming/{document.id}/oa-doc-wrapped.json",
                        ContentFile(oa_doc_wrapped_resp.content),
                    ),
                )
        except Exception as e:
            logger.exception(e)
            DocumentHistoryItem.objects.create(
                is_error=True,
                type="error",
                document=document,
                message="Error: OA document wrap failed",
                object_body=str(e),
            )
            document.status = Document.STATUS_FAILED
            document.verification_status = Document.V_STATUS_ERROR
            document.workflow_status = Document.WORKFLOW_STATUS_NOT_ISSUED  # Error?
            document.save()
            return False

        # now the OA document contains attachment (binary, if any) and CoO EDI3 document
        # and it's prepared for the notarisation
        oa_wrapped_body = oa_doc_wrapped_resp.content.decode("utf-8")

        # step4. encrypt and publish ciphertext
        # oa_wrapped_body
        (
            document.oa.iv_base64,
            document.oa.tag_base64,
            document.oa.ciphertext,
        ) = self._aes_encrypt(oa_wrapped_body, document.oa.key)
        document.oa.save()
        DocumentHistoryItem.objects.create(
            type="text",
            document=document,
            message="OA document encrypted and ciphertext saved",
        )

        # step5. Notarize the document
        if NotaryService.notarize_file(subject, oa_wrapped_body):
            DocumentHistoryItem.objects.create(
                type="text",
                document=document,
                message="OA document has been sent to the notary service",
            )
            document_oa_verify.apply_async(args=[document.pk], countdown=30)
        else:
            DocumentHistoryItem.objects.create(
                is_error=True,
                type="error",
                document=document,
                message="OA document has NOT been sent to the notary service",
            )
            document.verification_status = Document.V_STATUS_ERROR

        # and now goes the standard Intergov node communication
        self._send_igl_message(document, oa_wrapped_body, wrapped_doc_merkle_root)
        return True

    def _send_igl_message(self, document, oa_wrapped_body, wrapped_doc_merkle_root):
        if str(document.importing_country).upper() in config.IGL_CHANNELS_CONFIGURED.upper().split(","):
            document.status = Document.STATUS_PENDING
            document.save()
            # step6. Upload OA document to the node
            oa_uploaded_info = self.ig_client.post_text_document(
                document.importing_country, oa_wrapped_body
            )
            if oa_uploaded_info:
                DocumentHistoryItem.objects.create(
                    type="text",
                    document=document,
                    message="Uploaded OA document as a message object",
                    object_body=json.dumps(oa_uploaded_info),
                )
            else:
                DocumentHistoryItem.objects.create(
                    is_error=True,
                    type="error",
                    document=document,
                    message="Error: Can't upload OA document as a message object",
                )
                document.status = Document.STATUS_FAILED
                document.save()
                return False

            # Post the message
            message_json = self._render_intergov_message(
                document,
                subject=wrapped_doc_merkle_root,
                obj_multihash=oa_uploaded_info["multihash"],
            )
            posted_message = self.ig_client.post_message(message_json)
            if not posted_message:
                DocumentHistoryItem.objects.create(
                    is_error=True,
                    type="error",
                    document=document,
                    message="Error: unable to post Node message",
                    object_body=message_json,
                )
                document.status = Document.STATUS_FAILED
                document.save()
                return False
            document.workflow_status = Document.WORKFLOW_STATUS_ISSUED
            document.save()

            msg = NodeMessage.objects.create(
                status=NodeMessage.STATUS_SENT,
                document=document,
                sender_ref=posted_message["sender_ref"],
                subject=posted_message["subject"],
                body=posted_message,
                history=[f"Posted with status {posted_message['status']}"],
                is_outbound=True,
            )
            DocumentHistoryItem.objects.create(
                type="nodemessage",
                document=document,
                message="The node message has been dispatched",
                object_body=json.dumps(posted_message),
                linked_obj_id=msg.id,
            )

            logging.info("Posted message %s", posted_message)
            self._subscribe_to_message_updates(posted_message)
        else:
            DocumentHistoryItem.objects.create(
                type="message",
                document=document,
                message="Not sending the IGL message - the receiver is not in supported channels list",
            )
            document.workflow_status = Document.WORKFLOW_STATUS_ISSUED
            document.status = Document.STATUS_NOT_SENT
            document.save()

    def _render_uploaded_files(self, document: Document) -> list:
        uploaded = []
        for file in document.files.all():
            file.file
            mt, enc = mimetypes.guess_type(file.filename, strict=False)
            uploaded.append(
                {
                    "type": mt or "binary/octet-stream",
                    "filename": file.filename,
                    "data": base64.b64encode(file.file.read()).decode("utf-8"),
                }
            )
        return uploaded

    def _render_oa_v2_document(self, document: Document, subject: str) -> dict:
        tt_host = settings.OA_NOTARY_DOMAIN or settings.BASE_URL
        tt_key_location = tt_host.replace("https://", "").replace(
            "http://", ""
        )

        if ":" in tt_key_location:
            tt_key_location = tt_key_location.split(":", maxsplit=1)[0]

        doc = {
            "version": "open-attestation/2.0",
            "reference": subject,
            "name": f"OA document for {document.get_type_display()}",
            "validFrom": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "$template": {
                "name": "COO",
                "type": "EMBEDDED_RENDERER",
                "url": settings.OA_RENDERER_HOST,
                # "url": "https://chafta.tradetrust.io"
            },
            # OAv2 field
            "issuers": [
                {
                    "name": document.issuer.name,
                    "documentStore": settings.OA_NOTARY_CONTRACT,
                    "identityProof": {
                        "type": "DNS-TXT",
                        "location": tt_key_location,
                    },
                }
            ],
            # we have it in the certificate itself now, so no point to duplicate
            # "attachments": self._render_uploaded_files(document),
            "recipient": {
                "name": document.importer_name or "",
            },
        }
        return doc

    def _aes_encrypt(self, opentext, key):
        cipher = AESCipher(key)
        return cipher.encrypt_with_params_separate(opentext)

    def _render_intergov_message(
        self, document: Document, subject: str, obj_multihash: str
    ) -> dict:
        return {
            "predicate": Predicates.CoO_ISSUED,
            "sender": settings.ICL_APP_COUNTRY,
            "receiver": str(document.importing_country),
            "subject": subject,
            "obj": obj_multihash,
        }

    def _subscribe_to_message_updates(self, message: dict) -> None:
        # subscribe to new messages about the same conversation

        # TODO: message POST endpoint should return the subscription details
        # but now we just guessing it

        try:
            subj = message["subject"].replace(
                ".", "-"
            )  # FIXME: otherwise subscr go crazy
            self.ig_client.subscribe(
                predicate=f"subject.{subj}.status",
                callback=(
                    settings.ICL_TRADE_PORTAL_HOST
                    + reverse("websub:conversation-ping", args=[message["subject"]])
                ),
            )
        except Exception as e:
            logger.exception(e)
        # subscribe to updates on this message
        try:
            self.ig_client.subscribe(
                predicate=f"message.{message['sender_ref']}.status",
                callback=(
                    settings.ICL_TRADE_PORTAL_HOST
                    + reverse(
                        "websub:message-thin-ping",
                        args=[message["sender"] + ":" + message["sender_ref"]],
                    )
                ),
            )
        except Exception as e:
            logger.exception(e)


class NodeService(BaseIgService):
    def update_message_by_sender_ref(self, sender_ref: str) -> bool:
        """
        We received some light notification about the message updated,
        so now need to determine what the `cred` is, find that message and get
        it's status
        """
        if ":" not in sender_ref:
            # wrong format, must be provided
            logger.error("Sender_ref in the wrong format: no sender")
            return False

        sender, short_sender_ref = sender_ref.split(":", maxsplit=1)
        node_msg = NodeMessage.objects.filter(sender_ref=short_sender_ref).first()
        if not node_msg:
            logger.error(
                "Got request to update message status by sender ref but "
                "can't find the message"
            )
            raise self.retry()  # exc=exc
        # 1. retrieve message from the intergov
        msg_body = self.ig_client.retrieve_message(sender_ref)
        # 2. update status in the local database
        if not msg_body:
            logger.error(
                "Processing notification about message which can't "
                "be retrieved from the message API"
            )
            return False
        if msg_body["status"] != node_msg.body["status"]:
            node_msg.history.append(
                f"Changed status from {node_msg.body['status']} to {msg_body['status']}"
            )
            node_msg.body = msg_body

            if msg_body["status"] == "accepted":
                node_msg.status = NodeMessage.STATUS_ACCEPTED
            elif msg_body["status"] == "rejected":
                node_msg.status = NodeMessage.STATUS_REJECTED
            node_msg.save()

        # 3. optional processing steps (send reply/ack msg, etc)
        node_msg.trigger_processing(new_status=msg_body["status"])
        return True

    def subscribe_to_new_messages(self) -> None:
        if not settings.IGL_APIS.get("subscription"):
            # do not subscribe because the subscription API is not configured
            return
        result = self.ig_client.subscribe(
            predicate="message.*",
            callback=(
                settings.ICL_TRADE_PORTAL_HOST + reverse("websub:message-incoming")
            ),
        )
        if result:
            logger.info("Re-subscribed to predicate message.*")

    def store_message_by_ping_body(self, ping_body: dict) -> bool:
        # Once new message notification arrives we have message sender ref
        # and have to retrieve it
        # Example of the body:
        # {
        #    'predicate': 'message.519c81d5-5cdd-4643-960c-cad49dbb06bd.status',
        #    'sender_ref': 'CN:519c81d5-5cdd-4643-960c-cad49dbb06bd'
        # }
        sender_ref = ping_body["sender_ref"]

        # 1. retrieve it
        msg_body = self.ig_client.retrieve_message(sender_ref)
        # 2. handle it locally (attaching to some document, etc)
        if not msg_body:
            logger.error(
                "Processing notification about message which can't "
                "be retrieved from the message API"
            )
            return False
        # try to get existing document with the same subject
        first_fit_message = (
            NodeMessage.objects.exclude(document__isnull=True)
            .filter(
                subject=msg_body["subject"],
            )
            .first()
        )
        if first_fit_message:
            document = first_fit_message.document
        else:
            document = None
        if not first_fit_message or not document:
            # start a new conversation
            logger.info("Starting a new document/conversation for %s", msg_body)
            self._start_new_conversation(msg_body)
        else:
            msg, created = NodeMessage.objects.get_or_create(
                sender_ref=msg_body["sender_ref"],
                defaults=dict(
                    document=document,
                    status=NodeMessage.STATUS_INBOUND,
                    subject=msg_body["subject"],
                    is_outbound=False,
                    body=msg_body,
                    history=[
                        f"Received at {timezone.now()}",
                    ],
                ),
            )
            if created:
                msg.trigger_processing()
            else:
                logger.info(
                    "Message %s is already in the system", msg_body["sender_ref"]
                )
        return True

    def _start_new_conversation(self, message_body: dict) -> None:
        from trade_portal.documents.tasks import process_incoming_document_received

        NEW_DOC_PREDICATES = [
            Predicates.CoO_ISSUED,
            Predicates.SDO_CREATED,
            Predicates.CO_CREATED,
        ]
        if message_body["predicate"] not in NEW_DOC_PREDICATES:
            logger.warning(
                "Received conversation starting message with predicate %s which is not a document-starting",
                message_body["predicate"],
            )
            return

        oad = OaDetails.objects.create(
            created_for=None,
            uri="",
            key="",
        )
        new_doc = Document.objects.create(
            oa=oad,
            created_by_org=None,
            status=Document.STATUS_INCOMING,
            workflow_status=Document.WORKFLOW_STATUS_INCOMING,
            verification_status=Document.V_STATUS_NOT_STARTED,
            sending_jurisdiction=message_body["sender"],
            importing_country=message_body["receiver"],
            intergov_details=message_body,
        )
        logger.info("Created document %s for message %s", new_doc, message_body)
        msg, message_created = NodeMessage.objects.get_or_create(
            sender_ref=message_body["sender_ref"],
            is_outbound=False,
            defaults=dict(
                document=new_doc,
                status=NodeMessage.STATUS_INBOUND,
                subject=message_body["subject"],
                is_outbound=False,
                body=message_body,
                history=[
                    f"Received at {timezone.now()}",
                ],
            ),
        )
        DocumentHistoryItem.objects.create(
            type="nodemessage",
            document=new_doc,
            message=(
                "First message in the conversation has been received and "
                "the document processing has been scheduled in the background"
            ),
            object_body=json.dumps(message_body),
            linked_obj_id=msg.pk,
        )
        process_incoming_document_received.apply_async([new_doc.pk], countdown=2)
        return
