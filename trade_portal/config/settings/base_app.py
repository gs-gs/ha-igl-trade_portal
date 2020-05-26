import logging
from . import Env

env = Env()

ICL_CHAMBERS_APP_COUNTRY = env('ICL_CHAMBERS_APP_COUNTRY', default='AU')
ICL_APP_COUNTRY = ICL_CHAMBERS_APP_COUNTRY

CHAMBERS_ORG_NAME = env(
    'ICL_CHAMBERS_ORG_NAME',
    default=f"Chambers {ICL_APP_COUNTRY}"
)
CHAMBERS_ORG_ID = env(
    'ICL_CHAMBERS_ORG_ID',
    default=f"{CHAMBERS_ORG_NAME.replace(' ', '_')}.{ICL_APP_COUNTRY}"
)

# for the WebSub notifications
ICL_CHAMBERS_APP_HOST = env(
    'ICL_CHAMBERS_APP_HOST',
    default='http://trau-trade-portal-django.au-ig-apis-external:8050'
)

# Just for the UI skin
CSS_COUNTRY = env(
    'ICL_CSS_COUNTRY',
    default='SG'
).lower()
if CSS_COUNTRY not in ('au', 'sg', 'cn'):
    logging.warning("Country %s is not supported", CSS_COUNTRY)

# Variables related to UI<>node auth
IGL_OAUTH_CLIENT_ID = env("IGL_OAUTH_CLIENT_ID", default=None)
IGL_OAUTH_CLIENT_SECRET = env("IGL_OAUTH_CLIENT_SECRET", default=None)
IGL_OAUTH_WELLKNOWN_URL = env("IGL_OAUTH_WELLKNOWN_URL", default=None)
IGL_OAUTH_SCOPES = env("IGL_OAUTH_SCOPES", default=None)
