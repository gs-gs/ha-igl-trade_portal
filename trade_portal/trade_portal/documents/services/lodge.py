"""
Things related to the CoO packaging, notarizing and sending to the upstream
"""
import json
import logging

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from trade_portal.documents.models import (
    Document,
    DocumentHistoryItem,
)
from trade_portal.documents.services.encryption import AESCipher
from trade_portal.documents.services.igl import IGLService
from trade_portal.documents.services.notarize import NotaryService
from trade_portal.documents.services.oa import OaApiRestClient, OaV2Renderer

logger = logging.getLogger(__name__)


class DocumentService:
    def __init__(self, oa_client=None, *args, **kwargs):
        if not oa_client:
            oa_client = OaApiRestClient()
        self.oa_client = oa_client
        self.ig_client = kwargs.pop("ig_client", None)
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

        # step 2. Render the OAv2 doc as JSON dict
        oa_doc = OaV2Renderer().render_oa_v2_document(document, subject)
        # step 2. Append EDI3 document, merging it to the OA root level
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
        # and it's prepared for the notarisation and further steps
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
        if NotaryService().notarize_file(oa_wrapped_body):
            DocumentHistoryItem.objects.create(
                type="text",
                document=document,
                message="OA document has been sent to the notary service",
            )
            # Calling this is not strictly required and is used just to ensure the verification went fine
            document_oa_verify.apply_async(args=[document.pk], countdown=30)
        else:
            # please note it doesn't stop the further steps and just marks verification
            # status as failure
            DocumentHistoryItem.objects.create(
                document=document,
                is_error=True, type="error",
                message="Error while notarizing the OA document"
            )
            # think about retrying it?
            document.verification_status = Document.V_STATUS_ERROR

        # and now goes the standard Intergov node communication
        IGLService(
            ig_client=self.ig_client
        ).send_igl_message(
            document, oa_wrapped_body, wrapped_doc_merkle_root
        )
        return True

    def _aes_encrypt(self, opentext, key):
        cipher = AESCipher(key)
        return cipher.encrypt_with_params_separate(opentext)
