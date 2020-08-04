import logging

from django.conf import settings
from config import celery_app

from trade_portal.legi.abr import fetch_abn_info
from trade_portal.users.models import Organisation


logger = logging.getLogger(__name__)


@celery_app.task(ignore_result=True,
                 max_retries=3, interval_start=10, interval_step=10, interval_max=50)
def update_org_fields(org_id):
    """
    For freshly created org
    Makes a request to a business register (if supported for that country)
    And fills the organisation name and other fields
    """
    org = Organisation.objects.get(pk=org_id)

    if settings.ICL_APP_COUNTRY == "AU":
        try:
            abn_info = fetch_abn_info(org.business_id)
        except Exception as e:
            logger.exception(e)
        else:
            business_name = abn_info.get("EntityName") or ""
            entity_code = abn_info.get("EntityTypeCode") or "org"
            if business_name:
                org.name = business_name
                org.dot_separated_id = f"{org.business_id}.{entity_code}.{settings.BID_NAME}"
                org.save()
                logger.info("Organisation %s name has been updated", org)
    return
