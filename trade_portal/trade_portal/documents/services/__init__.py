from django.conf import settings

from intergov_client import IntergovClient
from intergov_client.auth import DjangoCachedCognitoOIDCAuth, DumbAuth


class BaseIgService:
    """
    Class ensuring that there is IG client instance created
    to avoid code duplication and make it simpler.
    """

    def __init__(self, ig_client=None):
        if not ig_client:
            ig_client = self._get_ig_client()
        self.ig_client = ig_client

    def _get_ig_client(self) -> IntergovClient:
        if settings.IGL_OAUTH_WELLKNOWN_URL:
            ig_token_url = DjangoCachedCognitoOIDCAuth.resolve_wellknown_to_token_url(
                settings.IGL_OAUTH_WELLKNOWN_URL
            )
            ig_auth_class = DjangoCachedCognitoOIDCAuth(
                token_url=ig_token_url,
                client_id=settings.IGL_OAUTH_CLIENT_ID,
                client_secret=settings.IGL_OAUTH_CLIENT_SECRET,
                scope=settings.IGL_OAUTH_SCOPES,
            )
        else:
            ig_auth_class = DumbAuth()
        ig_client = IntergovClient(
            country=settings.ICL_APP_COUNTRY,
            endpoints=settings.IGL_APIS,
            auth_class=ig_auth_class
        )
        return ig_client
