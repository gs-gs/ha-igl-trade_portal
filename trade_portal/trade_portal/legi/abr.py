import json
import logging
import requests

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


def fetch_abn_info(abn):
    try:
        int(abn)
    except (ValueError, TypeError):
        return None
    if not abn or len(abn) != 11:
        return None

    if getattr(settings, "DUMB_ABR_REQUESTS", False):
        return {
            "Abn": str(abn),
            "AbnStatus": "Active",
            "Acn": "",
            "AddressDate": "2014-09-20",
            "AddressPostcode": "4815",
            "AddressState": "QLD",
            "BusinessName": [],
            "EntityName": "CATS, THERE ARE",
            "EntityTypeCode": "IND",
            "EntityTypeName": "Individual/Sole Trader",
            "Gst": None,
            "Message": "",
        }

    if settings.ABR_UUID:
        return fetch_abn_info_api(abn)
    else:
        logger.warning("ABR UUID is not configured")
        return {}


def fetch_abn_info_api(abn):
    """
    {
        'Abn': '16685967308',
        'AbnStatus': 'Cancelled',
        'Acn': '',
        'AddressDate': '2014-09-20',
        'AddressPostcode': '4815', 'AddressState': 'QLD',
        'BusinessName': [], 'EntityName': 'CATS, PETER ANDREW',
        'EntityTypeCode': 'IND', 'EntityTypeName': 'Individual/Sole Trader',
        'Gst': None,
        'Message': ''
    }
    """
    CACHE_KEY = f"abr_info_{int(abn)}"
    result = cache.get(CACHE_KEY)
    if result:
        return result

    result = {
        "snippet": "none",
        "postcode": "",
        "region": "",
        "legal_name": "",
    }
    resp = requests.get(
        "https://abr.business.gov.au/json/AbnDetails.aspx",
        {"callback": "callback", "abn": abn, "guid": settings.ABR_UUID},
    )
    if resp.status_code != 200:
        logger.warning("ABR request ended with the status code %s", resp.status_code)
        return result
    body = resp.content.decode("utf-8")
    if body.startswith("callback"):
        body = body[len("callback") :]
    body = body.strip("(").strip(")")
    body = json.loads(body)

    cache.set(CACHE_KEY, body, 3600 * 48)  # 2 days
    return body
