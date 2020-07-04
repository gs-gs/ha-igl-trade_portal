"""
Things related to the CoO packaging and sending to the upstream
"""
import base64
import datetime
import json
import logging
import mimetypes
from Crypto.Cipher import AES
from Crypto import Random

import requests
from constance import config
from django.conf import settings
from django.urls import reverse
from django.utils import timezone

from intergov_client import IntergovClient
from intergov_client.predicates import Predicates
from intergov_client.auth import DjangoCachedCognitoOIDCAuth, DumbAuth

from trade_portal.documents.models import (
    Document, DocumentHistoryItem, NodeMessage,
)

logger = logging.getLogger(__name__)


class AESCipher:
    BS = 256 // 8

    def __init__(self, key):
        self.key = bytes.fromhex(key)

    def pad(self, s):
        return s + (self.BS - len(s) % self.BS) * chr(self.BS - len(s) % self.BS)

    def unpad(self, s):
        return s[:-ord(s[len(s)-1:])]

    def encrypt(self, raw):
        raw = self.pad(raw)
        iv = Random.new().read(AES.block_size)
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return base64.b64encode(iv + cipher.encrypt(raw))

    def decrypt(self, enc):
        enc = base64.b64decode(enc)
        iv = enc[:16]
        cipher = AES.new(self.key, AES.MODE_CBC, iv)
        return self.unpad(cipher.decrypt(enc[16:]))


class BaseIgService:

    def __init__(self, ig_client=None):
        if not ig_client:
            ig_client = self._get_ig_client()
        self.ig_client = ig_client

    def _get_ig_client(self):
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

    def issue(self, document):
        assert document.status == Document.STATUS_ISSUED

        subject = "{}.{}.{}".format(
            settings.ICL_APP_COUNTRY.upper(),
            (
                document.created_by_org.business_id or "chambers-app"
            ).replace('.', '-'),
            document.short_id,
        )

        # step 1. Render things to be attached to the OA doc
        uploaded_files_rendered = self._render_uploaded_files(document)
        uploaded_files_rendered.append(
            {
                "type": "EDI3-document",
                "filename": "edi3_coo.json",
                # "mimeType": "application/json",
                "mimeType": "application/pdf",
                "data": base64.b64encode(
                    json.dumps(
                        document.get_rendered_edi3_document()
                    ).encode("utf-8")
                ).decode("utf-8")
            }
        )

        # step 2. Render the OA doc
        oa_doc = self._render_oa_document(
            document, subject, uploaded_files_rendered
        )
        # TODO: should we save oa_doc somewhere just for debug and fun?
        # document.oa.cleartext = json.dumps(oa_doc)
        # document.oa.save()

        DocumentHistoryItem.objects.create(
            type="text",
            document=document,
            message=f"OA document has been generated, size: {len(json.dumps(oa_doc))}b",
            object_body=json.dumps(oa_doc)
        )

        # step 3, slow: wrap OA document using external api for wrapping documents
        try:
            oa_doc_wrapped_resp = requests.post(
                config.OA_WRAP_API_URL + "/document/wrap",
                json={
                    "document": oa_doc,
                }
            )
        except Exception as e:
            logger.exception(e)
            DocumentHistoryItem.objects.create(
                type="error",
                document=document,
                message=(
                    f"Error: OA document wrap failed with error {str(e)}"
                ),
                object_body=oa_doc_wrapped_resp.json(),
            )
            document.status = Document.STATUS_ERROR
            document.save()
            return False

        if oa_doc_wrapped_resp.status_code == 200:
            oa_doc_wrapped = oa_doc_wrapped_resp.json()
            oa_doc_wrapped_json = json.dumps(oa_doc_wrapped)
            DocumentHistoryItem.objects.create(
                type="text",
                document=document,
                message=f"OA document has been wrapped, new size: {len(oa_doc_wrapped_json)}b",
                object_body=oa_doc_wrapped_json
            )
        else:
            logger.warning("Received responce %s for oa doc wrap step", oa_doc_wrapped_resp)
            DocumentHistoryItem.objects.create(
                type="error",
                document=document,
                message=(
                    f"Error: OA document wrap failed with result {oa_doc_wrapped_resp.status_code}"
                ),
                object_body=oa_doc_wrapped_resp.json(),
            )
            document.status = Document.STATUS_ERROR
            document.save()
            return False

        # now the OA document contains attachment (binary, if any) and CoO EDI3 document
        # and it's prepared for the notarisation

        oa_wrapped_body = json.dumps(oa_doc_wrapped)

        # step4. encrypt and publish ciphertext
        # oa_wrapped_body
        document.oa.ciphertext = self._aes_encrypt(
            oa_wrapped_body,
            document.oa.key
        ).decode("utf-8")
        document.oa.save()
        DocumentHistoryItem.objects.create(
            type="text",
            document=document,
            message="OA document encrypted and ciphertext saved",
        )

        # step5. Notarize the document
        logger.warning("We should notarize document %s now but it's not implemented", document)

        # and not the standard Intergov node communication
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
                type="error",
                document=document,
                message=(
                    "Error: Can't upload OA document as a message object"
                ),
                object_body=oa_doc_wrapped_resp.json(),
            )
            document.status = Document.STATUS_ERROR
            document.save()
            return False

        # Post the message
        message_json = self._render_intergov_message(
            document,
            subject=subject,
            obj_multihash=oa_uploaded_info['multihash']
        )
        posted_message = self.ig_client.post_message(message_json)
        if not posted_message:
            DocumentHistoryItem.objects.create(
                document=document,
                message="Error: unable to post Node message",
                object_body=message_json
            )
            document.status = Document.STATUS_ERROR
            document.save()
            return False
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
            type="nodemessage",
            document=document,
            message="The node message has been dispatched",
            object_body=json.dumps(posted_message),
            linked_obj_id=msg.id,
        )

        logging.info("Posted message %s", posted_message)
        self._subscribe_to_message_updates(posted_message)
        return

    def _render_uploaded_files(self, document):
        uploaded = []
        for file in document.files.all():
            file.file
            mt, enc = mimetypes.guess_type(file.filename, strict=False)
            uploaded.append(
                {
                    "type": "DocumentVerification2018",
                    "filename": file.filename,
                    "mimeType": mt or 'binary/octet-stream',
                    "data": base64.b64encode(file.file.read()).decode("utf-8")
                }
            )
        return uploaded

    def _render_oa_document(self, document, subject, attachments):
        doc = {
            "reference": subject,
            "name": f"OA document for {document.get_type_display()}",
            "validFrom": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "template": {
                # TODO
                "name": "CUSTOM_TEMPLATE",
                "type": "EMBEDDED_RENDERER",
                "url": "https://TODO.todo/renderer"
            },
            "issuer": {
                "id": settings.BASE_URL.replace(
                    '://',
                    f'://{document.issuer.business_id}.'
                ),
                "name": document.issuer.name,
                "identityProof": {
                    "type": "DNS-TXT",
                    "location": settings.BASE_URL,
                }
            },
            "proof": {
                "type": "OpenAttestationSignature2018",
                "method": "DOCUMENT_STORE",
                "value": config.OA_NOTARY_CONTRACT
            },
            "attachments": attachments
        }
        return doc

    def _aes_encrypt(self, opentext, key):
        cipher = AESCipher(key)
        return cipher.encrypt(opentext)

    # def lodge(self, document):
    #     """
    #     Render document as a message and send it to the upstream
    #     * upload all documents which must be uploaded to the upstream
    #     * create the message.object
    #       * link uploaded documents there
    #     * upload message object as well
    #     * send the message, linking to message object, which links to uploaded docs
    #     * save all details to the certificate object just for fun
    #     """
    #     assert document.status == Document.STATUS_ISSUED

    #     # For each attached document we have - upload it to the intergov
    #     # ideally this should be a celery chord with retries and so on
    #     uploaded_documents_links = self._lodge_upload_files(document)

    #     # Upload the document itself
    #     # as a rendered JSON body in a machine-readable document
    #     cert_body_info = self.ig_client.post_text_document(
    #         document.importing_country, self._lodge_render_document(document)
    #     )
    #     uploaded_documents_links.append(
    #         {
    #             'TYPE1': 'certificate',
    #             'TYPE2': 'EDI3.draft.2020-05-26.01',
    #             'ct': 'application/json',
    #             'link': cert_body_info['multihash']
    #         }
    #     )
    #     logger.info(
    #         "The following documents were uploaded for %s: %s",
    #         document, uploaded_documents_links
    #     )

    #     # just save it for further reading
    #     document.intergov_details['links'] = uploaded_documents_links
    #     document.save()

    #     # upload the object itself. which is just some JSON linking to things
    #     object_info = self.ig_client.post_text_document(
    #         document.importing_country, self._render_obj_body(uploaded_documents_links)
    #     )
    #     logger.info("Uploaded certificate object %s", object_info)

    #     document.intergov_details['object_hash'] = object_info['multihash']
    #     document.save()

    #     # Post the message
    #     message_json = self._render_intergov_message(
    #         document,
    #         object_info['multihash']
    #     )
    #     posted_message = self.ig_client.post_message(message_json)
    #     if not posted_message:
    #         raise Exception("Unable to post message, trying again")
    #     document.save()

    #     NodeMessage.objects.create(
    #         status=NodeMessage.STATUS_SENT,
    #         document=document,
    #         sender_ref=posted_message["sender_ref"],
    #         subject=posted_message["subject"],
    #         body=posted_message,
    #         history=[
    #             f"Posted with status {posted_message['status']}"
    #         ],
    #         is_outbound=True
    #     )
    #     logging.info("Posted message %s", posted_message)
    #     self._subscribe_to_message_updates(posted_message)
    #     return

    # def _lodge_upload_files(self, document):
    #     uploaded = []

    #     for file in document.files.all():
    #         # upload the document
    #         d_info = self.ig_client.post_binary_document(
    #             str(document.importing_country),
    #             file.file
    #         )
    #         mt, enc = mimetypes.guess_type(file.filename, strict=False)
    #         uploaded.append(
    #             {
    #                 'TYPE1': 'document',
    #                 'TYPE2': "Attachment",
    #                 'name': file.filename,
    #                 'ct': mt or 'binary/octet-stream',
    #                 'link': d_info['multihash']
    #             }
    #         )
    #     return uploaded

    # def _lodge_render_document(self, document):
    #     return json.dumps(document.get_rendered_json())

    # def _render_obj_body(self, links):
    #     return json.dumps({
    #         # not much to include here by the way.
    #         # it's just links field is interesting
    #         'type': 'certificate-of-origin',
    #         'format': '0.0.2',
    #         'links': links,
    #     })

    def _render_intergov_message(self, document, subject, obj_multihash):
        return {
            "predicate": Predicates.CoO_ISSUED,
            "sender": settings.ICL_APP_COUNTRY,
            "receiver": str(document.importing_country),
            "subject": subject,
            "obj": obj_multihash,
        }

    def _subscribe_to_message_updates(self, message):
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

    def update_message_by_sender_ref(self, sender_ref):
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
        return

    def subscribe_to_new_messages(self):
        result = self.ig_client.subscribe(
            predicate="message.*",
            callback=(
                settings.ICL_TRADE_PORTAL_HOST +
                reverse("websub:message-incoming")
            ),
        )
        if result:
            logger.info("Re-subscribed to predicate message.*")

    def store_message_by_ping_body(self, ping_body):
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
            logger.warning("Received incoming message but can't find any conversation for it")
            return False
        msg, created = NodeMessage.objects.get_or_create(
            sender_ref=msg_body["sender_ref"],
            defaults=dict(
                document=document,
                status=msg_body["status"],
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
