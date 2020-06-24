import logging

from trade_portal.documents.services import NodeService
from config import celery_app as app

logger = logging.getLogger(__name__)


@app.task(ignore_result=True, max_retries=3)
def subscribe_to_notifications():
    NodeService().subscribe_to_new_messages()
