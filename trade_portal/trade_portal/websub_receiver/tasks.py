import logging

from trade_portal.documents.services.igl import IGLService
from config import celery_app as app

logger = logging.getLogger(__name__)


@app.task(ignore_result=True, max_retries=3)
def subscribe_to_new_messages():
    try:
        IGLService().subscribe_to_new_messages()
    except Exception as e:
        logger.exception(e)
