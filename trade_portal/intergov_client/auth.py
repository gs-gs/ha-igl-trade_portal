import base64
import logging

import requests

logger = logging.getLogger(__name__)


class BaseAuthClass:
    """
    all `get_..._header` functions return tuple (header_name, header_value, expires_in_int_sec)
    with values which allow a correct request to the node API.
    It's very implementation specific, but for the demo we use generic OIDC.
    """

    def get_document_auth_header(self):
        raise NotImplementedError()

    def get_message_auth_header(self):
        raise NotImplementedError()

    def get_subscr_auth_header(self):
        raise NotImplementedError()


class DumbAuth(BaseAuthClass):
    def get_document_auth_header(self):
        return "Authorization", "Dumb", 3600

    def get_message_auth_header(self):
        return "Authorization", "Dumb", 3600

    def get_subscr_auth_header(self):
        return "Authorization", "Dumb", 3600


class CognitoOIDCAuth(BaseAuthClass):

    @classmethod
    def resolve_wellknown_to_token_url(cls, wellknown_url):
        wellknown_content = requests.get(
            wellknown_url
        )
        assert wellknown_content.status_code == 200
        return wellknown_content.json().get("token_endpoint")

    def __init__(self, token_url, client_id, client_secret, scope):
        self.TOKEN_URL = token_url
        self.CLIENT_ID = client_id
        self.CLIENT_SECRET = client_secret
        self.SCOPE = scope

    def get_auth_header(self):
        cognito_auth = base64.b64encode(f"{self.CLIENT_ID}:{self.CLIENT_SECRET}".encode("utf-8")).decode("utf-8")
        token_resp = requests.post(
            self.TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": self.CLIENT_ID,
                "scope": self.SCOPE,
            },
            headers={
                'Authorization': f'Basic {cognito_auth}',
            }
        )
        assert token_resp.status_code == 200, token_resp.json()
        json_resp = token_resp.json()
        logger.info("Retrieved new JWT; ends in %s", json_resp['expires_in'])
        return (
            'Authorization',
            json_resp["access_token"],
            json_resp['expires_in']
        )

    def get_document_auth_header(self):
        return self.get_auth_header()

    def get_message_auth_header(self):
        return self.get_auth_header()

    def get_subscr_auth_header(self):
        return self.get_auth_header()


class DjangoCachedCognitoOIDCAuth(CognitoOIDCAuth):
    """
    Just in case there is some Django cache in place around...
    With local imports it shoudln't break things for users without it
    """

    @classmethod
    def resolve_wellknown_to_token_url(cls, wellknown_url):
        import hashlib
        from django.core.cache import cache

        wk_hash = hashlib.md5(wellknown_url.encode("utf-8")).hexdigest()
        cache_key = f"TOKEN_URL_FOR_{wk_hash}"

        existing_value = cache.get(cache_key)

        if existing_value:
            return existing_value

        token_endpoint = super().resolve_wellknown_to_token_url(wellknown_url)

        cache.set(cache_key, token_endpoint, 30)
        return token_endpoint

    def get_auth_header(self, *args, **kwargs):
        import hashlib
        from django.core.cache import cache
        cache_key = "auth_header_cache" + hashlib.md5(
            f"{self.CLIENT_ID}:{self.CLIENT_SECRET}:{self.SCOPE}".encode("utf-8")
        ).hexdigest()

        cached_value = cache.get(cache_key)
        if cached_value:
            return cached_value
        a, b, exp = super().get_auth_header(*args, **kwargs)
        cache.set(cache_key, (a, b, 0), exp - 60 if exp > 60 else exp / 2)
        return a, b, exp
