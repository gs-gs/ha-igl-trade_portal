from . import Env

env = Env()

# Contains endpoints set (document, subscriber, message APIs and other)
# based on different incoming env variables but always in the same format:
# {
#     "document": "http://domain.tld:port",
#     "message": "http://domain.tld:port",
#     "subscription": "http://domain.tld:port",
# }
IGL_APIS = {
    # always in the simplified format
    'subscription': env(
        "IGL_SUBSCRAPI_ENDPOINT",
        default='http://subscriptions_api:80'
    ),
}

# legacy variable values
if IGL_APIS["subscription"].endswith("/subscriptions"):
    IGL_APIS["subscription"] = IGL_APIS["subscription"][:-len("/subscriptions")]

IGL_MESSAGEAPI_ENDPOINT = env("IGL_MESSAGEAPI_ENDPOINT", default=None)
if IGL_MESSAGEAPI_ENDPOINT:
    # new style
    IGL_APIS["message"] = IGL_MESSAGEAPI_ENDPOINT
else:
    # old/IG style
    IGL_APIS["message"] = "{}://{}:{}".format(
        env("IGL_MESSAGEAPI_SCHEMA", default='http'),
        env('IGL_MESSAGEAPI_HOST', default='message_api'),
        env('IGL_MESSAGEAPI_PORT', default=env('IGL_MESSAGEAPPI_PORT', default='80')),
    )

IGL_DOCUMENTAPI_ENDPOINT = env("IGL_DOCUMENTAPI_ENDPOINT", default=None)
if IGL_DOCUMENTAPI_ENDPOINT:
    # new style
    IGL_APIS["document"] = IGL_DOCUMENTAPI_ENDPOINT
else:
    # old/IG style
    IGL_APIS["document"] = "{}://{}:{}".format(
        env("IGL_DOCAPI_SCHEMA", default='http'),
        env('IGL_DOCAPI_HOST', default='document_api'),
        env('IGL_DOCAPI_PORT', default='80'),
    )
