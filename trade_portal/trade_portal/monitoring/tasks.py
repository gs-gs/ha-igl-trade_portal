import logging

import ipinfo

from django.conf import settings
from config import celery_app
from trade_portal.monitoring.models import VerificationAttempt

logger = logging.getLogger(__name__)


@celery_app.task(
    max_retries=3,
    interval_start=10,
    interval_step=10,
    interval_max=50,
    time_limit=300,
    soft_time_limit=290,
)
def resolve_geoloc_ip(token_id, ip_addr):
    v = VerificationAttempt.objects.get(pk=token_id)
    if not settings.IPINFO_KEY:
        logger.warning("IP info is not configured - skipping the geolocation step")
    else:
        # TODO: cache it
        handler = ipinfo.getHandler(settings.IPINFO_KEY)
        details = handler.getDetails(ip_addr)
        details = details.all.copy()
        details.pop("ip", None)
        v.geo_info.update(details)
    v.save()
    return
