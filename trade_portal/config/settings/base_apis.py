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
        default='http://subscriptions_api:5000'
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
        env('IGL_MESSAGEAPI_PORT', default=env('IGL_MESSAGEAPPI_PORT', default='5000')),
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
        env('IGL_DOCAPI_PORT', default='5000'),
    )


ABR_UUID = env("ABR_UUID", default=None) or None


# The value required by notarisation workflow; must be set along with the OA_NOTARY_DOMAIN
OA_NOTARY_CONTRACT = env("OA_NOTARY_CONTRACT")
# The value required by notarisation workflow; this is the domain where value from the OA_NOTARY_CONTRACT
# is set in the DNS records. Coupled with OA_NOTARY_CONTRACT. Leave empty to use default website domain.
OA_NOTARY_DOMAIN = env("OA_NOTARY_DOMAIN")

# Either local or remote setup which is able to wrap documents
# (the API providing /wrap and /unwrap endpoints)
OA_WRAP_API_URL = env("OA_WRAP_API_URL")

# ## Variables needed for notarisastion step, which relies on buckets/queues
# ## may be replaced by other mechanisms once they are defined
# ## You could use AWS cloud, minio or AWS localstack to provide these values

# Do not send manual notifications if empty; must be available using the OA access keys
OA_UNPROCESSED_QUEUE_URL = env("OA_UNPROCESSED_QUEUE_URL")
# Just a plain bucket name, do not send files to notarisation if empty
OA_UNPROCESSED_BUCKET_NAME = env("OA_UNPROCESSED_BUCKET_NAME")

# Values in format accesskey:secretkey, None if empty (policy defined)
OA_AWS_ACCESS_KEYS = env("OA_AWS_ACCESS_KEYS", default="") or None

# Some endpoint (without any non-transparent auth) which verifies the OA JSON document passed to it
OA_VERIFY_API_URL = env("OA_VERIFY_API_URL")

# ## Universal actions QR code parameters

# Unversal actions QR code base host - the one handling that querysetring "
# and redirecting to the correct verify endpoint.",
UA_BASE_HOST = env("UA_BASE_HOST")
# Renderer we use by default; The host with protocol without trailing slash
OA_RENDERER_HOST = env("OA_RENDERER_HOST")


IPINFO_KEY = env("IPINFO_KEY", default=None) or None
