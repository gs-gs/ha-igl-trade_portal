import logging
import time

from django.conf import settings
from PyPDF2.utils import PdfReadError

from trade_portal.documents.models import (
    Document,
    DocumentHistoryItem,
)
from trade_portal.documents.services.lodge import DocumentService, NodeService
from trade_portal.documents.services.textract import MetadataExtractService
from trade_portal.documents.services.watermark import WatermarkService
from trade_portal.oa_verify.services import OaVerificationService
from config import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    ignore_result=True,
    max_retries=3,
    interval_start=10,
    interval_step=10,
    interval_max=50,
    time_limit=300,
    soft_time_limit=290,
)
def lodge_document(document_id=None):
    doc = Document.objects.get(pk=document_id)
    DocumentHistoryItem.objects.create(
        document=doc, message="Starting the issue step..."
    )

    try:
        WatermarkService().watermark_document(doc)
    except PdfReadError as e:
        # some PDF issue
        if e.args[0] == "file has not been decrypted":
            DocumentHistoryItem.objects.create(
                is_error=True,
                type="error",
                document=doc,
                message="Unable to issue the document: impossible to add the QR code to encrypted PDF",
                object_body=str(e),
            )
        else:
            # generic PDF issue
            DocumentHistoryItem.objects.create(
                is_error=True,
                type="error",
                document=doc,
                message=(
                    "Unable to issue the document: impossible to add the QR code "
                    "because the PDF is invalid or can't be parsed"
                ),
                object_body=str(e),
            )
        logger.exception(e)
        logger.info("Marking document %s as failed", doc)
        doc.workflow_status = Document.WORKFLOW_STATUS_NOT_ISSUED
        doc.status = Document.STATUS_FAILED
        doc.verification_status = Document.V_STATUS_FAILED
        doc.save()
        doc.files.filter(is_watermarked=False).update(is_watermarked=None)  # so they are not "processing" anymore
        return  # for any watermarking error we don't continue the process

    try:
        t0 = time.time()
        DocumentService().issue(doc)
        issue_time_spent = round(time.time() - t0, 4)
    except Exception as e:
        DocumentHistoryItem.objects.create(
            is_error=True,
            type="error",
            document=doc,
            message="Unable to issue the document: exception",
            object_body=str(e),
        )
        if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False) is True:
            # for local setups it's handy to raise exception
            raise
        logger.exception(e)
        if doc.status == Document.STATUS_PENDING:
            logger.info("Marking document %s as failed", doc)
            doc.status = Document.STATUS_FAILED
            doc.save()
    else:
        DocumentHistoryItem.objects.create(
            is_error=False,
            type="message",
            document=doc,
            message=f"The document issued in {issue_time_spent}s",
        )


@celery_app.task(
    bind=True,
    ignore_result=True,
    max_retries=3,
    interval_start=10,
    interval_step=10,
    interval_max=50,
)
def update_message_by_sender_ref(self, sender_ref):
    NodeService().update_message_by_sender_ref(sender_ref)


@celery_app.task(
    bind=True,
    ignore_result=True,
    max_retries=3,
    interval_start=10,
    interval_step=10,
    interval_max=50,
)
def store_message_by_ping_body(self, ping_body):
    NodeService().store_message_by_ping_body(ping_body)


@celery_app.task(bind=True, ignore_result=True, max_retries=40)
def process_incoming_document_received(self, document_pk):
    from trade_portal.documents.services.incoming import IncomingDocumentService

    doc = Document.objects.get(pk=document_pk)
    logger.info("Processing the incoming document %s", doc)
    try:
        IncomingDocumentService().process_new(doc)
    except Exception as e:
        if getattr(e, "is_retryable", None) is True:
            # try to retry (no document has been downloaded yet from the remote or something)
            if self.request.retries < self.max_retries:
                retry_delay = 15 + 5 * self.request.retries
                if self.request.retries > 10:  # worth to be worried
                    logger.exception(e)
                    # start to complain only if things get real
                    logger.warning(
                        "Retrying the doc %s processing task %sth time",
                        doc.pk,
                        self.request.retries,
                    )
                    DocumentHistoryItem.objects.create(
                        is_error=True,
                        type="error",
                        document=doc,
                        message=f"Error on retry {self.request.retries}, next attempt in {retry_delay}s",
                        object_body=str(e),
                    )
                self.retry(countdown=retry_delay)
            else:
                logger.error(
                    "Max retries reached for the document %s, marking as error (%s)", doc.pk, str(e)
                )
                DocumentHistoryItem.objects.create(
                    is_error=True,
                    type="error",
                    document=doc,
                    message=f"Unable to process document after {self.request.retries} retries",
                    object_body=str(e),
                )
                doc.status = Document.STATUS_FAILED
                doc.save()
                return False
        else:
            # non-retryable exception
            logger.exception(e)
            DocumentHistoryItem.objects.create(
                is_error=True,
                type="error",
                document=doc,
                message="Unable to process document, non-retryable exception",
                object_body=str(e),
            )
            doc.status = Document.STATUS_FAILED
            doc.save()
            return False
    else:
        logger.info("Incoming document %s processed without errors", doc)
    return


@celery_app.task(
    ignore_result=True,
    max_retries=3,
    interval_start=10,
    interval_step=10,
    interval_max=50,
)
def textract_document(document_id=None):
    return
    # TODO: when doing this mind slow processing and the fact that document file may change during it
    doc = Document.objects.get(pk=document_id)
    MetadataExtractService.extract(doc)


@celery_app.task(
    ignore_result=True,
    max_retries=3,
    interval_start=10,
    interval_step=10,
    interval_max=50,
)
def fill_document_metadata(document_id=None):
    """
    For document files uploaded
    Tries to retrieve first PDF page width/height and save to "metadata" field
    So QR code watermark UI functionality works fine for all possible QR code and page sizes
    And also saves flag for encrypted PDFs which we can't update
    Or invalid PDFs which we can't parse at all
    """
    logger.info("Trying to determine PDF metadata for document %s", document_id)
    doc = Document.objects.get(pk=document_id)
    for docfile in doc.files.all():
        if docfile.filename.lower().endswith(".pdf"):
            # not determined yet and is PDF
            t0 = time.time()
            x, y = WatermarkService().get_document_filesize(docfile)
            time_spent = round(time.time() - t0, 4)  # seconds

            docfile.refresh_from_db()
            if x == 0 and y == 0:
                docfile.metadata["unparseable_pdf"] = True
                DocumentHistoryItem.objects.create(
                    is_error=False,
                    type="message",
                    document=doc,
                    message=(
                        f"The PDF has been marked as readonly (can't be parsed),"
                        f" spent {time_spent}s"
                    )
                )
            elif x == -1 and y == -1:
                docfile.metadata["encrypted_pdf"] = True
                DocumentHistoryItem.objects.create(
                    is_error=False,
                    type="message",
                    document=doc,
                    message=(
                        f"The PDF has been marked as readonly (protected from updates),"
                        f" spent {time_spent}s"
                    )
                )
            else:
                DocumentHistoryItem.objects.create(
                    is_error=False,
                    type="message",
                    document=doc,
                    message=f"PDF page size determined to {x}x{y}, spent {time_spent}s",
                )
                docfile.metadata["width_mm"] = x
                docfile.metadata["height_mm"] = y
            docfile.save()  # fields=("metadata",)
    return


@celery_app.task(bind=True, ignore_result=True, max_retries=80)  # around 2 hours of retries
def document_oa_verify(self, document_id, do_retries=True):
    """
    When a new document is sent by us
    Or received from remote party
    We try to parse some OA document from it and verify it
    Changing the verification status
    """
    document = Document.objects.get(pk=document_id)
    logger.info(
        "Trying to verify document %s, attempt %s", document, self.request.retries
    )
    vc = document.get_vc()
    if not vc:
        document.verification_status = Document.V_STATUS_ERROR
        document.save()
        logger.info(
            "Unable to verify document: no VC can be retrieved for %s", document
        )
        DocumentHistoryItem.objects.create(
            is_error=True,
            type="error",
            document=document,
            message="Unable to verify document: no VC can be retrieved; it's either invalid or of non-OA format",
        )
        return
    else:
        # this is definitely OA, report that we have started the verification
        # which will either end in `valid` status or `failed` if we give up doing that
        if document.verification_status == Document.V_STATUS_NOT_STARTED:
            document.verification_status = Document.V_STATUS_PENDING
            document.save()
            DocumentHistoryItem.objects.create(
                type="OA",
                document=document,
                message="Verification started...",
            )

    verify_response = OaVerificationService().verify_file(vc.read())
    if verify_response.get("status") == "valid":
        document.verification_status = Document.V_STATUS_VALID
        document.save()
        DocumentHistoryItem.objects.create(
            type="OA",
            document=document,
            message="The document OA credential is valid",
        )
        return
    elif verify_response.get("status") == "error":
        document.verification_status = Document.V_STATUS_ERROR
        document.save()
        logger.error(
            "Unable to verify document: Error %s for %s",
            verify_response.get("error_message"),
            document,
        )
        DocumentHistoryItem.objects.create(
            is_error=True,
            type="error",
            document=document,
            message=f"Unable to verify document: {verify_response.get('error_message')}",
        )
        return
    if do_retries:
        if self.request.retries < self.max_retries:
            logger.info(
                "Retrying the document %s verification task (%s)",
                document,
                self.request.retries,
            )
            if self.request.retries < 10:
                retry_delay = 30  # seconds
            else:
                retry_delay = 120  # seconds

            if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False) is True:
                logger.warning("Not retrying the eager task")
            else:
                self.retry(countdown=retry_delay)
        else:
            # max retries but still not valid - mark as failed
            document.verification_status = Document.V_STATUS_FAILED
            document.save()
            DocumentHistoryItem.objects.create(
                is_error=True,
                type="error",
                document=document,
                message=f"Unable to verify the document after {self.request.retries} attempts",
            )
    else:
        logger.info("not scheduling any retries because started directly")
