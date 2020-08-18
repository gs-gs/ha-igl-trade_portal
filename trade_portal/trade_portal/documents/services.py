"""
Things related to the CoO packaging and sending to the upstream
"""
import base64
import datetime
import json
import io
import logging
import mimetypes
import uuid

# TODO: replace to pyca/cryptography as Bandit advises (low)
from Crypto.Cipher import AES

import dateutil.parser
import requests
from constance import config
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.urls import reverse
from django.utils import timezone

from intergov_client import IntergovClient
from intergov_client.predicates import Predicates
from intergov_client.auth import DjangoCachedCognitoOIDCAuth, DumbAuth

from trade_portal.documents.models import (
    FTA, Party, Document, DocumentHistoryItem,
    NodeMessage, OaDetails, DocumentFile,
)

logger = logging.getLogger(__name__)


class IncomingDocumentProcessingError(Exception):
    def __init__(self, *args, **kwargs):
        self.is_retryable = kwargs.pop("is_retryable", False)
        super().__init__(*args, **kwargs)


class AESCipher:
    BS = 256 // 8

    def __init__(self, key):
        self.key = bytes.fromhex(key)

    def pad(self, s):
        return s + (self.BS - len(s) % self.BS) * chr(self.BS - len(s) % self.BS)

    def unpad(self, s):
        return s[:-ord(s[len(s)-1:])]

    def encrypt_with_params_separate(self, raw):
        encoded = base64.b64encode(raw.encode("utf-8"))
        cipher = AES.new(self.key, AES.MODE_GCM)
        ciphertext, tag = cipher.encrypt_and_digest(encoded)
        return (
            base64.b64encode(cipher.nonce).decode("utf-8"),
            base64.b64encode(tag).decode("utf-8"),
            base64.b64encode(ciphertext).decode("utf-8")
        )

    def decrypt(self, iv, tag, ciphertext):
        iv = base64.b64decode(iv)
        tag = base64.b64decode(tag)
        ciphertext = base64.b64decode(ciphertext)
        cipher = AES.new(self.key, AES.MODE_EAX, iv)
        return cipher.decrypt_and_verify(ciphertext, tag)


class BaseIgService:

    def __init__(self, ig_client=None):
        if not ig_client:
            ig_client = self._get_ig_client()
        self.ig_client = ig_client

    def _get_ig_client(self) -> IntergovClient:
        if settings.IGL_OAUTH_WELLKNOWN_URL:
            ig_token_url = DjangoCachedCognitoOIDCAuth.resolve_wellknown_to_token_url(
                settings.IGL_OAUTH_WELLKNOWN_URL
            )
            ig_auth_class = DjangoCachedCognitoOIDCAuth(
                token_url=ig_token_url,
                client_id=settings.IGL_OAUTH_CLIENT_ID,
                client_secret=settings.IGL_OAUTH_CLIENT_SECRET,
                scope=settings.IGL_OAUTH_SCOPES,
            )
        else:
            ig_auth_class = DumbAuth()
        ig_client = IntergovClient(
            country=settings.ICL_APP_COUNTRY,
            endpoints=settings.IGL_APIS,
            auth_class=ig_auth_class
        )
        return ig_client


class DocumentService(BaseIgService):

    def issue(self, document: Document) -> bool:
        subject = "{}.{}.{}".format(
            settings.ICL_APP_COUNTRY.upper(),
            (
                document.created_by_org.business_id
            ).replace('.', '-'),
            document.short_id,
        )

        # step 2. Render the OAv2 doc with attachments
        oa_doc = self._render_oa_v2_document(
            document, subject
        )
        # step 2. Append EDI3 document, merging them on the root level
        oa_doc.update(document.get_rendered_edi3_document())

        DocumentHistoryItem.objects.create(
            type="text", document=document,
            message=f"OA document has been generated, size: {len(json.dumps(oa_doc))}b",
            # object_body=json.dumps(oa_doc)
            related_file=default_storage.save(
                f'incoming/{document.id}/oa-doc.json',
                ContentFile(json.dumps(oa_doc, indent=2).encode("utf-8"))
            )
        )

        # step 3, slow: wrap OA document using external api for wrapping documents
        try:
            oa_doc_wrapped_resp = requests.post(
                config.OA_WRAP_API_URL + "/document/wrap",
                json={
                    "document": oa_doc,
                    "params": {
                        "version": 'https://schema.openattestation.com/2.0/schema.json',
                    }
                }
            )
        except Exception as e:
            logger.exception(e)
            DocumentHistoryItem.objects.create(
                type="error", document=document,
                message="Error: OA document wrap failed with error",
                object_body=str(e),
            )
            document.status = Document.STATUS_FAILED
            document.save()
            return False

        if oa_doc_wrapped_resp.status_code == 200:
            oa_doc_wrapped = oa_doc_wrapped_resp.json()
            wrapped_doc_merkle_root = oa_doc_wrapped.get("signature", {}).get("merkleRoot") or subject
            oa_doc_wrapped_json = json.dumps(oa_doc_wrapped)
            DocumentHistoryItem.objects.create(
                type="text", document=document,
                message=f"OA document has been wrapped, new size: {len(oa_doc_wrapped_json)}b",
                related_file=default_storage.save(
                    f'incoming/{document.id}/oa-doc-wrapped.json',
                    ContentFile(oa_doc_wrapped_json.encode("utf-8"))
                )
            )
        else:
            logger.warning("Received responce %s for oa doc wrap step", oa_doc_wrapped_resp)
            DocumentHistoryItem.objects.create(
                type="error", document=document,
                message=f"Error: OA document wrap failed with result {oa_doc_wrapped_resp.status_code}",
                object_body=oa_doc_wrapped_resp.json(),
            )
            document.status = Document.STATUS_FAILED
            document.save()
            return False

        # now the OA document contains attachment (binary, if any) and CoO EDI3 document
        # and it's prepared for the notarisation

        oa_wrapped_body = json.dumps(oa_doc_wrapped)

        # step4. encrypt and publish ciphertext
        # oa_wrapped_body
        (
            document.oa.iv_base64, document.oa.tag_base64, document.oa.ciphertext
        ) = self._aes_encrypt(
            oa_wrapped_body,
            document.oa.key
        )
        document.oa.save()
        DocumentHistoryItem.objects.create(
            type="text", document=document,
            message="OA document encrypted and ciphertext saved",
        )

        # step5. Notarize the document
        if NotaryService.notarize_file(subject, oa_wrapped_body):
            DocumentHistoryItem.objects.create(
                type="text", document=document,
                message="OA document has been sent to the notary service",
            )
        else:
            DocumentHistoryItem.objects.create(
                type="error", document=document,
                message="OA document has NOT been sent to the notary service",
            )

        # and not the standard Intergov node communication
        # step6. Upload OA document to the node
        oa_uploaded_info = self.ig_client.post_text_document(
            document.importing_country, oa_wrapped_body
        )
        if oa_uploaded_info:
            DocumentHistoryItem.objects.create(
                type="text", document=document,
                message="Uploaded OA document as a message object",
                object_body=json.dumps(oa_uploaded_info),
            )
        else:
            DocumentHistoryItem.objects.create(
                type="error", document=document,
                message="Error: Can't upload OA document as a message object",
            )
            document.status = Document.STATUS_FAILED
            document.save()
            return False

        # Post the message
        message_json = self._render_intergov_message(
            document,
            subject=wrapped_doc_merkle_root,
            obj_multihash=oa_uploaded_info['multihash']
        )
        posted_message = self.ig_client.post_message(message_json)
        if not posted_message:
            DocumentHistoryItem.objects.create(
                type="error", document=document,
                message="Error: unable to post Node message",
                object_body=message_json
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
            history=[
                f"Posted with status {posted_message['status']}"
            ],
            is_outbound=True
        )
        DocumentHistoryItem.objects.create(
            type="nodemessage", document=document,
            message="The node message has been dispatched",
            object_body=json.dumps(posted_message), linked_obj_id=msg.id,
        )

        logging.info("Posted message %s", posted_message)
        self._subscribe_to_message_updates(posted_message)
        return True

    def _render_uploaded_files(self, document: Document) -> list:
        uploaded = []
        for file in document.files.all():
            file.file
            mt, enc = mimetypes.guess_type(file.filename, strict=False)
            uploaded.append(
                {
                    "type": mt or 'binary/octet-stream',
                    "filename": file.filename,
                    "data": base64.b64encode(file.file.read()).decode("utf-8")
                }
            )
        return uploaded

    def _render_oa_v2_document(self, document: Document, subject: str) -> dict:
        tt_key_location = settings.BASE_URL.replace("https://", "").replace("http://", "")

        if ":" in tt_key_location:
            tt_key_location = tt_key_location.split(':', maxsplit=1)[0]

        doc = {
            "version": "open-attestation/2.0",
            "reference": subject,
            "name": f"OA document for {document.get_type_display()}",
            "validFrom": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "$template": {
              "name": "custom",
              "type": "EMBEDDED_RENDERER",
              "url": "https://chafta.tradetrust.io"
            },
            # OAv2 field
            "issuers": [
                {
                  "name": document.issuer.name,
                  "documentStore": config.OA_NOTARY_CONTRACT,
                  "identityProof": {
                    "type": "DNS-TXT",
                    "location": tt_key_location,
                  }
                }
              ],
            "attachments": self._render_uploaded_files(document),
            "recipient": {
                "name": document.importer_name or "",
            },
        }
        return doc

    def _aes_encrypt(self, opentext, key):
        cipher = AESCipher(key)
        return cipher.encrypt_with_params_separate(opentext)

    def _render_intergov_message(self, document: Document, subject: str, obj_multihash: str) -> dict:
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
            subj = message['subject'].replace(".", "-")  # FIXME: otherwise subscr go crazy
            self.ig_client.subscribe(
                predicate=f"subject.{subj}.status",
                callback=(
                    settings.ICL_TRADE_PORTAL_HOST +
                    reverse("websub:conversation-ping", args=[
                        message['subject']
                    ])
                ),
            )
        except Exception as e:
            logger.exception(e)
        # subscribe to updates on this message
        try:
            self.ig_client.subscribe(
                predicate=f"message.{message['sender_ref']}.status",
                callback=(
                    settings.ICL_TRADE_PORTAL_HOST +
                    reverse("websub:message-thin-ping", args=[
                        message['sender'] + ":" + message['sender_ref']
                    ])
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
        node_msg = NodeMessage.objects.filter(
            sender_ref=short_sender_ref
        ).first()
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
        node_msg.trigger_processing(
            new_status=msg_body["status"]
        )
        return True

    def subscribe_to_new_messages(self) -> None:
        result = self.ig_client.subscribe(
            predicate="message.*",
            callback=(
                settings.ICL_TRADE_PORTAL_HOST +
                reverse("websub:message-incoming")
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
        first_fit_message = NodeMessage.objects.exclude(
            document__isnull=True
        ).filter(
            subject=msg_body["subject"],
        ).first()
        if first_fit_message:
            document = first_fit_message.document
        else:
            document = None
        if not first_fit_message or not document:
            # start a new conversation
            logger.info("Starting a new document/conversation for the %s", msg_body)
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
                    ]
                )
            )
            if created:
                msg.trigger_processing()
            else:
                logger.info("Message %s is already in the system", msg_body["sender_ref"])
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
                message_body["predicate"]
            )
            return

        oad = OaDetails.objects.create(
            created_for=None,
            uri="(empty)"
        )
        new_doc = Document.objects.create(
            oa=oad,
            created_by_org=None,
            status=Document.STATUS_INCOMING,
            sending_jurisdiction=message_body["sender"],
            importing_country=message_body["receiver"],
            intergov_details=message_body,
        )
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
                ]
            )
        )
        DocumentHistoryItem.objects.create(
            type="nodemessage", document=new_doc,
            message=(
                "First message in the conversation has been received and "
                "the document processing has been scheduled in the background"
            ),
            object_body=json.dumps(message_body),
            linked_obj_id=msg.pk,
        )
        process_incoming_document_received.apply_async(
            [new_doc.pk],
            countdown=2
        )
        return


class NotaryService():
    """
    Service made solely for files notarisation.
    In it's current state it just puts some file to some bucket and ensurees that
    remote OA worker will be informed about it.

    In the future it could also handle notifiations from that service and handle
    possible errors (the OA service is very sensitive to format issues)
    """

    @classmethod
    def notarize_file(cls, doc_key: str, document_body: str):
        import boto3  # local import because some setups may not even use it

        if not config.OA_UNPROCESSED_BUCKET_NAME:
            logger.warning("Asked to notarize file but the service is not configured well")
            return False

        s3_config = {
            'aws_access_key_id': config.OA_AWS_ACCESS_KEYS.split(":")[0] or None,
            'aws_secret_access_key': config.OA_AWS_ACCESS_KEYS.split(":")[1] or None,
            'region_name': None,
        }
        s3res = boto3.resource('s3', **s3_config).Bucket(config.OA_UNPROCESSED_BUCKET_NAME)

        body = document_body.encode('utf-8')
        content_length = len(body)

        date = str(timezone.now().date())
        key = f"{date}/{doc_key}.json"
        s3res.Object(key).put(
            Body=body,
            ContentLength=content_length
        )
        logger.info("The file %s to be notarized has been uploaded", key)
        cls.send_manual_notification(key)
        return True

    @classmethod
    def send_manual_notification(cls, key: str):
        """
        If the bucket itself doesn't send these notifications for some reason
        We forge it so worker is aware. Another side effect is that we can
        change the notification format, including our custom parameters
        """
        import boto3  # local import because some setups may not even use it

        if not config.OA_UNPROCESSED_QUEUE_URL:
            # it's fine, we don't want to send them
            return

        s3_config = {
            'aws_access_key_id': config.OA_AWS_ACCESS_KEYS.split(":")[0] or None,
            'aws_secret_access_key': config.OA_AWS_ACCESS_KEYS.split(":")[1] or None,
            'region_name': 'ap-southeast-2',
        }

        unprocessed_queue = boto3.resource('sqs', **s3_config).Queue(
            config.OA_UNPROCESSED_QUEUE_URL
        )
        unprocessed_queue.send_message(MessageBody=json.dumps({
           "Records": [
              {
                 "s3": {
                    "bucket": {
                       "name": config.OA_UNPROCESSED_BUCKET_NAME
                    },
                    "object": {
                       "key": key
                    }
                 }
              }
           ]
        }))
        logger.info("The notification about file %s to be notarized has been sent", key)
        return


class IncomingDocumentService(BaseIgService):

    def process_new(self, doc: Document):
        DocumentHistoryItem.objects.create(
            type="text", document=doc,
            message="Started the incoming document retrieval..."
        )
        # 1. Download the obj from the document API
        try:
            binary_obj_content = self.ig_client.retrieve_document(
                doc.intergov_details["obj"],
            )
        except Exception as e:
            raise IncomingDocumentProcessingError(str(e), is_retryable=True)
        # 2. Save the object somewhere (it could be binary or text file)
        # do we have it already?
        try:
            the_file = DocumentFile.objects.filter(
                doc=doc,
                filename=doc.intergov_details["obj"]
            ).first()
            if the_file:
                logger.info("We already have that file, funny")
            else:
                the_file = DocumentFile.objects.create(
                    doc=doc,
                    filename=doc.intergov_details["obj"],
                    size=len(binary_obj_content),
                )

            path = default_storage.save(
                f'incoming/{doc.id}/{doc.intergov_details["obj"]}.json',
                ContentFile(binary_obj_content)
            )
            # TODO: kill the old file before?
            the_file.file = path
            the_file.save()
        except Exception as e:
            DocumentHistoryItem.objects.create(
                type="error", document=doc,
                message="Failed to store obj from the message",
                object_body=str(e),
            )
            doc.status = Document.STATUS_FAILED
            doc.save()
            return False

        DocumentHistoryItem.objects.create(
            type="docfile", document=doc,
            message="Downloaded the obj from the root message",
            object_body=the_file.filename,
            linked_obj_id=the_file.pk
        )
        # we have saved the obj file, now we are able to parse it
        try:
            self.get_incoming_document_format(doc, binary_obj_content)
        except Exception as e:
            logger.exception(e)
            self._complain_and_die(
                doc,
                "Unable to render the object attached to this message",
            )
        return True

    def get_incoming_document_format(self, doc: Document, binary_obj_content):
        try:
            json_content = json.loads(binary_obj_content)
        except Exception:
            json_content = None

        if json_content:
            logger.info("Found some JSON obj for incoming document %s", doc)
        else:
            return self._complain_and_die(
                doc,
                "Incoming document has no supported obj (can't parse it)"
            )
            return False

        if not isinstance(json_content, dict):
            return self._complain_and_die(
                doc,
                "While incoming document %s obj is json - it's still unsupported",
                doc
            )
            return False

        oa_version = json_content.get("version")
        supported_versions = (
            "https://schema.openattestation.com/2.0/schema.json",
            "https://schema.openattestation.com/3.0/schema.json"
        )

        if oa_version not in supported_versions:
            return self._complain_and_die(
                doc,
                "Incoming document %s obj format '%s' is not supported",
                doc, oa_version
            )

        # wow, it's even OA document
        DocumentHistoryItem.objects.create(
            type="message", document=doc,
            message="Found OA document",
            object_body=oa_version
        )

        try:
            unwrapped_oa = requests.post(
                config.OA_WRAP_API_URL + "/document/unwrap",
                json={
                    "document": json_content,
                    "params": {
                        "version": oa_version,
                    }
                }
            ).json()
        except Exception as e:
            logger.exception(e)
            return self._complain_and_die(
                doc,
                "Can't unwrap %s document for %s",
                oa_version, doc,
            )

        if oa_version == "https://schema.openattestation.com/2.0/schema.json":
            self._process_oa2_document(doc, unwrapped_oa)
        elif oa_version == "https://schema.openattestation.com/3.0/schema.json":
            self._process_oa3_document(doc, unwrapped_oa)
        return True

    def _process_oa2_document(self, doc: Document, data: dict):
        attachments = data.pop("attachments")
        for attach in attachments:
            bin_file = base64.b64decode(attach["data"].encode("utf-8"))
            af = DocumentFile.objects.create(
                doc=doc,
                # type=type,
                filename=attach.get("filename") or "unknown.bin",
                size=len(bin_file)
            )
            path = default_storage.save(
                f'incoming/{doc.id}/attach-{str(uuid.uuid4())}',
                ContentFile(bin_file)
            )
            af.file = path
            af.save()

        doc.document_number = data.get("id")

        try:
            # these actions are dangerous in terms of exceptions,
            # so we use catchall to handle them one by one if they occure

            issueDateTime = data.get("issueDateTime")
            if issueDateTime:
                issueDateTime = dateutil.parser.isoparse(issueDateTime)
                if issueDateTime:
                    doc.created_at = issueDateTime

            if (data.get("name") or "").lower().endswith("Certificate of Origin".lower()):
                # Certificate of Origin
                if data.get("isPreferential") is True:
                    doc.type = Document.TYPE_PREF_COO
                if data.get("isPreferential") is False:
                    doc.type = Document.TYPE_NONPREF_COO
            supplyChainConsignment = data.get("supplyChainConsignment") or {}
            if supplyChainConsignment:
                exporter = supplyChainConsignment.get("exporter") or {}
                if exporter:
                    doc.exporter, created = Party.objects.get_or_create(
                        created_by_org=doc.created_by_org,
                        business_id=exporter.get("id"),
                        type=Party.TYPE_TRADER,
                        country=doc.sending_jurisdiction,
                        defaults={
                            "name": exporter.get("name") or "",
                        }
                    )
            issuer = data.get("issuer")
            if issuer:
                doc.issuer, created = Party.objects.get_or_create(
                    created_by_org=doc.created_by_org,
                    business_id=issuer.get("id"),
                    country=doc.sending_jurisdiction,
                    defaults={
                        "name": issuer.get("name") or "",
                    }
                )
            freeTradeAgreement = data.get("freeTradeAgreement")
            if freeTradeAgreement:
                try:
                    doc.fta = FTA.objects.get(name=freeTradeAgreement)
                except Exception:
                    logger.warning(
                        "The FTA %s is passed in the inbound document but can't be found locally",
                        freeTradeAgreement
                    )
            importer = data.get("importer", {})
            if importer and isinstance(importer, dict):
                importer_name = importer.get("name")
                doc.importer_name = importer_name

        except Exception as e:
            logger.exception(e)
        doc.intergov_details["oa_doc"] = data
        doc.save()
        return

    def _process_oa3_document(self, doc: Document, data: dict):
        return self._complain_and_die(
            doc,
            "Sorry, we don't support OAv3 documents yet",
        )

    def _complain_and_die(self, doc: Document, message, *message_args):
        logger.info(message, *message_args)
        DocumentHistoryItem.objects.create(
            type="error", document=doc,
            message=message % message_args,
        )
        return False


class WatermarkService:
    """
    Helper to add QR code to the uploaded PDF file assuming it doesn't have any
    """
    def watermark_document(self, document: Document):
        qrcode_image = document.oa.get_qr_image()
        for docfile in document.files.filter(is_watermarked=False):
            if docfile.filename.lower().endswith(".pdf"):
                self.add_watermark(docfile, qrcode_image)
        return

    def add_watermark(self, docfile: DocumentFile, qrcode_image) -> None:
        """
        Draws given QR code over a PDF content in the top right cornder
        and re-saves the file in place with updated result
        """
        # Local imports are used in case this functionality is disabled
        # for some setups/envs
        import PIL
        from reportlab.pdfgen import canvas
        from reportlab.lib.utils import ImageReader
        from reportlab.lib.units import cm
        from reportlab.lib.pagesizes import A4
        from PyPDF2 import PdfFileWriter, PdfFileReader

        logging.info("Adding a watermark for %s", docfile)
        qrcode_image = PIL.Image.open(io.BytesIO(qrcode_image))

        # Prepare the PDF document containing only QR code
        qrcode_stream = io.BytesIO()
        c = canvas.Canvas(qrcode_stream, pagesize=A4)
        c.drawImage(
            ImageReader(qrcode_image),
            A4[0] - 3 * cm - 1 * cm, A4[1] - 3 * cm - 1 * cm,
            width=3*cm, height=3*cm, preserveAspectRatio=1,
        )
        c.save()

        qrcode_stream.seek(0)
        qrcode_doc = PdfFileReader(qrcode_stream)
        orig_doc = PdfFileReader(docfile.original_file or docfile.file)
        output_file = PdfFileWriter()

        for page_number in range(orig_doc.getNumPages()):
            input_page = orig_doc.getPage(page_number)
            if page_number == 0:
                # only for the first page
                input_page.mergePage(qrcode_doc.getPage(0))
            output_file.addPage(input_page)

        outputStream = io.BytesIO()
        output_file.write(outputStream)

        old_filename_parts = docfile.file.name.rsplit(".", maxsplit=1)
        new_filename = ".".join([
            old_filename_parts[0].rstrip(".altered"),
            "altered",
            old_filename_parts[1]
        ])
        outputStream.seek(0)
        new_saved_filename = default_storage.save(
            new_filename,
            ContentFile(outputStream.read())
        )
        docfile.file = new_saved_filename
        logger.info("Saved altered PDF file as %s", new_saved_filename)
        docfile.is_watermarked = True
        docfile.save()
        return
