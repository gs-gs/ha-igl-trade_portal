import logging

from django.conf import settings

from trade_portal.documents.models import (
    Document, DocumentHistoryItem,
)
from trade_portal.documents.services import DocumentService, NodeService
from config import celery_app

logger = logging.getLogger(__name__)


# @app.task
# def notify_about_certificate_created(certificate_id):
#     c = Document.objects.get(pk=certificate_id)
#     send_mail(
#         'Certificate application has been approved',
#         """Just letting you know that your certificate {} has been lodged""".format(
#             c
#         ),
#         settings.DEFAULT_FROM_EMAIL,
#         [c.created_by.email],
#         fail_silently=False,
#     )


@celery_app.task(ignore_result=True,
                 max_retries=3, interval_start=10, interval_step=10, interval_max=50)
def lodge_document(document_id=None):
    doc = Document.objects.get(pk=document_id)
    DocumentHistoryItem.objects.create(
        document=doc,
        message="Starting the issue step..."
    )
    try:
        DocumentService().issue(doc)
    except Exception as e:
        if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False) is True:
            # for local setups it's handy to raise exception
            raise
        logger.exception(e)
        if doc.status == Document.STATUS_ISSUED:
            logger.info("Marking document %s as error", doc)
            doc.status = Document.STATUS_ERROR
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
    from trade_portal.documents.services import IncomingDocumentService

    doc = Document.objects.get(pk=document_pk)
    logger.info("Processing the incoming document %s", doc)
    try:
        IncomingDocumentService().process_new(doc)
    except Exception as e:
        if getattr(e, "is_retryable", None) is True:
            # try to retry (no document has been downloaded yet from the remote or something)
            if self.request.retries < self.max_retries:
                logger.warning(
                    "Retrying the doc %s processing task %sth time",
                    doc,
                    self.request.retries
                )
                DocumentHistoryItem.objects.create(
                    type="error", document=doc,
                    message="Error, will be trying again",
                    object_body=str(e),
                )
                self.retry(countdown=5 + 10 * self.request.retries)
            else:
                logger.error("Max retries reached for the document %s, marking as error", doc)
                DocumentHistoryItem.objects.create(
                    type="error", document=doc,
                    message=f"Unable to process document after {self.request.retries} retries",
                    object_body=str(e),
                )
                doc.status = Document.STATUS_ERROR
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
            doc.status = Document.STATUS_ERROR
            doc.save()
            return False
    return
