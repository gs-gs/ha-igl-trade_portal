import hashlib
import json
import logging

import requests

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


def isabn(obj):
    """isabn(string or int) -> True|False

    Validate an ABN (Australian Business Number).
    http://www.ato.gov.au/businesses/content.asp?doc=/content/13187.htm

    Accepts an int or a string of exactly 11 digits and no leading zeroes.
    Digits may be optionally separated with spaces. Any other input raises
    TypeError or ValueError.

    Return True if the argument is a valid ABN, otherwise False.

    >>> isabn('53 004 085 616')
    True
    >>> isabn('93 004 085 616')
    False

    """
    if isinstance(obj, int):
        if not 10**10 <= obj < 10**11:
            raise ValueError('int out of range for an ABN')
        obj = str(obj)
        assert len(obj) == 11
    if not isinstance(obj, str):
        raise TypeError('expected a str or int but got %s' % type(obj))
    obj = obj.replace(' ', '')
    if len(obj) != 11:
        raise ValueError('ABN must have exactly 11 digits')
    if not obj.isdigit():
        raise ValueError('non-digit found in ABN')
    if obj.startswith('0'):
        raise ValueError('leading zero not allowed in ABNs')
    digits = [int(c) for c in obj]
    digits[0] -= 1
    weights = [10, 1, 3, 5, 7, 9, 11, 13, 15, 17, 19]
    assert len(digits) == len(weights) == 11
    chksum = sum(d * w for d, w in zip(digits, weights)) % 89
    return chksum == 0


def fetch_abn_info(abn):
    try:
        int(abn)
    except (ValueError, TypeError):
        return None
    if not abn or len(abn) != 11:
        return None
    if not isabn(abn):
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


def search_entities_by_name(search_term):
    CACHE_KEY = f'org_by_name_{hashlib.md5(search_term.encode("utf-8")).hexdigest().lower()}'
    result = cache.get(CACHE_KEY)
    if result:
        return result

    resp = requests.get(
        "https://abr.business.gov.au/json/MatchingNames.aspx",
        {"name": search_term, "maxResults": 20, "guid": settings.ABR_UUID},
    )
    if resp.status_code != 200:
        logger.warning("ABR request ended with the status code %s", resp.status_code)
        return {
            "status": "error",
            "message": f"ABR status code {resp.status_code} - please try again later"
        }
    body = resp.content.decode("utf-8")
    if body.startswith("callback"):
        body = body[len("callback") :]
    body = body.strip("(").strip(")")
    body = json.loads(body)

    if body.get("Message"):
        # has message -> means error
        return {
            "status": "error",
            "message": body.get("Message"),
        }

    result = {
        "status": "success",
        "names": body.get("Names"),
    }
    cache.set(CACHE_KEY, result, 3600 * 48)  # 2 days
    return result
