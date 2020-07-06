import logging
from . import Env

env = Env()

ICL_TRADE_PORTAL_COUNTRY = env(
    'ICL_TRADE_PORTAL_COUNTRY',
    default=env("ICL_COUNTRY", default="AU")
)
ICL_APP_COUNTRY = ICL_TRADE_PORTAL_COUNTRY

# for the WebSub notifications
ICL_TRADE_PORTAL_HOST = env(
    'ICL_TRADE_PORTAL_HOST',
    default='http://trau-trade-portal-django.igl-node-au-ig-apis-external:8050'
)
if ICL_TRADE_PORTAL_HOST.endswith("/"):
    ICL_TRADE_PORTAL_HOST = ICL_TRADE_PORTAL_HOST[:-1]


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
