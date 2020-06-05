"""
Things related to the CoO packaging and sending to the upstream
"""
import json
import logging
import mimetypes

from django.conf import settings
from django.urls import reverse

from intergov_client import IntergovClient
from intergov_client.auth import DjangoCachedCognitoOIDCAuth, DumbAuth

from trade_portal.documents.models import (
    Document, NodeMessage,
)

logger = logging.getLogger(__name__)


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

    def lodge(self, document):
        """
        Render document as a message and send it to the upstream
        * upload all documents which must be uploaded to the upstream
        * create the message.object
          * link uploaded documents there
        * upload message object as well
        * send the message, linking to message object, which links to uploaded docs
        * save all details to the certificate object just for fun
        """
        assert document.status == Document.STATUS_ISSUED

        # For each attached document we have - upload it to the intergov
        # ideally this should be a celery chord with retries and so on
        uploaded_documents_links = self._lodge_upload_files(document)

        # Upload the document itself
        # as a rendered JSON body in a machine-readable document
        cert_body_info = self.ig_client.post_text_document(
            document.importing_country, self._lodge_render_document(document)
        )
        uploaded_documents_links.append(
            {
                'TYPE1': 'certificate',
                'TYPE2': 'EDI3.draft.2020-05-26.01',
                'ct': 'application/json',
                'link': cert_body_info['multihash']
            }
        )
        logger.info(
            "The following documents were uploaded for %s: %s",
            document, uploaded_documents_links
        )

        # just save it for further reading
        document.intergov_details['links'] = uploaded_documents_links
        document.save()

        # upload the object itself. which is just some JSON linking to things
        object_info = self.ig_client.post_text_document(
            document.importing_country, self._render_obj_body(uploaded_documents_links)
        )
        logger.info("Uploaded certificate object %s", object_info)

        document.intergov_details['object_hash'] = object_info['multihash']
        document.save()

        # Post the message
        message_json = self._render_intergov_message(
            document,
            object_info['multihash']
        )
        posted_message = self.ig_client.post_message(message_json)
        if not posted_message:
            raise Exception("Unable to post message, trying again")
        document.save()

        NodeMessage.objects.create(
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
        logging.info("Posted message %s", posted_message)
        self._subscribe_to_message_updates(posted_message)
        return

    def _lodge_upload_files(self, document):
        uploaded = []

        for file in document.files.all():
            # upload the document
            d_info = self.ig_client.post_binary_document(
                str(document.importing_country),
                file.file
            )
            mt, enc = mimetypes.guess_type(file.filename, strict=False)
            uploaded.append(
                {
                    'TYPE1': 'document',
                    'TYPE2': "Attachment",
                    'name': file.filename,
                    'ct': mt or 'binary/octet-stream',
                    'link': d_info['multihash']
                }
            )
        return uploaded

    def _lodge_render_document(self, document):
        return json.dumps({
            "TYPE": document.get_type_display(),
            "FORMAT": "EDI3.draft.2020-05-26.01",  # TODO: UN.blabla.edi3.2019-06.1

            'id': str(document.pk),
            'importing_country': str(document.importing_country),
            'org.name': str(document.created_by_org),
            'body': {
                'importer_info': document.importer_name,
                'document_number': document.document_number or '',
                'consignment_ref': document.consignment_ref or '',
                'issuer': str(document.issuer or ''),
                'exporter': str(document.exporter or ''),
                'fta': str(document.fta or ''),
                'created_at': str(document.created_at),
            }
        })

    def _render_obj_body(self, links):
        return json.dumps({
            # not much to include here by the way.
            # it's just links field is interesting
            'type': 'certificate-of-origin',
            'format': '0.0.2',
            'links': links,
        })

    def _render_intergov_message(self, document, obj_multihash):
        return {
            "predicate": "UN.CEFACT.Trade.CertificateOfOrigin.created",
            "sender": settings.ICL_APP_COUNTRY,
            "receiver": str(document.importing_country),
            "subject": "{}.{}.{}".format(
                settings.ICL_APP_COUNTRY.upper(),
                (
                    document.created_by_org.business_id or "chambers-app"
                ).replace('.', '-'),
                document.short_id,
            ),
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
