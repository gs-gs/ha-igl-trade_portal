import logging

from django.conf import settings

from trade_portal.documents.models import (
    Document, DocumentHistoryItem,
)
from trade_portal.documents.services.lodge import DocumentService, NodeService
from trade_portal.documents.services.textract import MetadataExtractService
from trade_portal.documents.services.watermark import WatermarkService
from trade_portal.oa_verify.services import OaVerificationService
from config import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(ignore_result=True,
                 max_retries=3, interval_start=10, interval_step=10, interval_max=50)
def lodge_document(document_id=None):
    doc = Document.objects.get(pk=document_id)
    DocumentHistoryItem.objects.create(
        document=doc,
        message="Starting the issue step..."
    )

    WatermarkService().watermark_document(doc)

    try:
        DocumentService().issue(doc)
    except Exception as e:
        if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False) is True:
            # for local setups it's handy to raise exception
            raise
        logger.exception(e)
        if doc.status == Document.STATUS_PENDING:
            logger.info("Marking document %s as failed", doc)
            doc.status = Document.STATUS_FAILED
            doc.save()


@celery_app.task(bind=True, ignore_result=True,
                 max_retries=3, interval_start=10, interval_step=10, interval_max=50)
def update_message_by_sender_ref(self, sender_ref):
    NodeService().update_message_by_sender_ref(sender_ref)


@celery_app.task(bind=True, ignore_result=True,
                 max_retries=3, interval_start=10, interval_step=10, interval_max=50)
def store_message_by_ping_body(self, ping_body):
    NodeService().store_message_by_ping_body(ping_body)


@celery_app.task(bind=True, ignore_result=True, max_retries=6)
def process_incoming_document_received(self, document_pk):
    from trade_portal.documents.services.incoming import IncomingDocumentService

    doc = Document.objects.get(pk=document_pk)
    logger.info("Processing the incoming document %s", doc)
    try:
        IncomingDocumentService().process_new(doc)
    except Exception as e:
        logger.exception(e)
        if getattr(e, "is_retryable", None) is True:
            # try to retry (no document has been downloaded yet from the remote or something)
            if self.request.retries < self.max_retries:
                logger.warning(
                    "Retrying the doc %s processing task %sth time",
                    doc,
                    self.request.retries
                )
                retry_delay = 15 + 30 * self.request.retries
                DocumentHistoryItem.objects.create(
                    type="error", document=doc,
                    message=f"Error, will be trying again in {retry_delay}s",
                    object_body=str(e),
                )
                self.retry(countdown=retry_delay)
            else:
                logger.error("Max retries reached for the document %s, marking as error", doc)
                DocumentHistoryItem.objects.create(
                    type="error", document=doc,
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
                type="error", document=doc,
                message="Unable to process document, non-retryable exception",
                object_body=str(e),
            )
            doc.status = Document.STATUS_FAILED
            doc.save()
            return False
    else:
        logger.info("Incoming document %s processed without errors", doc)
    return


@celery_app.task(ignore_result=True,
                 max_retries=3, interval_start=10, interval_step=10, interval_max=50)
def textract_document(document_id=None):
    return
    doc = Document.objects.get(pk=document_id)
    MetadataExtractService.extract(doc)


@celery_app.task(bind=True, ignore_result=True, max_retries=10)
def verify_own_document(self, document_id):
    document = Document.objects.get(pk=document_id)
    logger.info(
        "Trying to verify own document %s, attempt %s",
        document,
        self.request.retries
    )
    vc = document.get_vc()
    if not vc:
        document.verification_status = Document.V_STATUS_ERROR
        document.save()
        logger.error("Unable to retrieve OA file for the document %s", document)
        return

    is_valid = OaVerificationService().verify_file(vc)
    if is_valid is True:
        document.verification_status = Document.V_STATUS_VALID
        document.save()
        return
    if self.request.retries < self.max_retries:
        logger.warning(
            "Retrying own document %s verification task (%s)",
            document,
            self.request.retries
        )
        retry_delay = 15 + 30 * self.request.retries

        if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False) is True:
            logger.warning("Not retrying the eager task")
        else:
            self.retry(countdown=retry_delay)
    else:
        # max retries but still not valid - mark as failed
        document.verification_status = Document.V_STATUS_FAILED
        document.save()
        DocumentHistoryItem.objects.create(
            type="error", document=document,
            message=f"Unable to verify own document after {self.request.retries} attempts",
        )
