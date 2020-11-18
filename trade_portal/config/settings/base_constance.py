from . import Env

env = Env()

CONSTANCE_BACKEND = "constance.backends.database.DatabaseBackend"

CONSTANCE_CONFIG = {
    "ENABLE_CAPTCHA": (
        False,
        "Use Google ReCaptchaV3; disable for legal or debug/hotfix reasons; "
        "enable otherwise once configured correctly",
    ),
    "FEEDBACK_EMAIL": (
        "",
        "Where to send the feedback notifications to; "
        "empty to not send them to any email and just save to the database; "
        "some shared inbox is recommended",
    ),
    "OA_NOTARY_CONTRACT": (
        "0xa57812DeC86336809Ea68987AbaA1669DeA31541",
        "The value required by notarisation workflow; must be set along with the OA_NOTARY_DOMAIN",
    ),
    "OA_NOTARY_DOMAIN": (
        "",
        "The value required by notarisation workflow; this is the domain where value from the OA_NOTARY_CONTRACT"
        "is set in the DNS records. Coupled with OA_NOTARY_CONTRACT. Leave empty to use default website domain.",
    ),
    "OA_WRAP_API_URL": (
        "http://docker-host:9090",
        "Either local or remote setup which is able to wrap documents "
        "(the API providing /wrap and /unwrap endpoints)",
    ),
    # Variables needed for notarisastion step, which relies on buckets/queues
    # may be replaced by other mechanisms once they are defined
    # You could use AWS cloud, minio or AWS localstack to provide these values
    "OA_UNPROCESSED_QUEUE_URL": (
        "",
        "Do not send manual notifications if empty; must be available using the OA access keys",
    ),
    "OA_UNPROCESSED_BUCKET_NAME": (
        "",
        "Just a plain bucket name, do not send files to notarisation if empty",
    ),
    "OA_AWS_ACCESS_KEYS": (
        ":",
        "Values in format accesskey:secretkey, None if empty (policy defined)",
    ),
    "OA_VERIFY_API_URL": (
        "https://openattverify.c1.devnet.trustbridge.io/verify/fragments",
        "Some endpoint (without any non-transparent auth) which verifies the OA JSON document passed to it",
    ),
    # misc
    "USERS_NOTIFICATIONS_MAILBOX": (
        "",
        "The email where new notifications about registered users/etc will be sent",
    ),
    # Universal actions QR code parameters
    "UA_BASE_HOST": (
        "https://trade.c1.devnet.trustbridge.io/v/",
        "Unversal actions QR code base host - the one handling that querysetring "
        "and redirecting to the correct verify endpoint.",
    ),
    # Renderer we use by default
    "OA_RENDERER_HOST": (
        "https://renderer-openatt.c2.devnet.trustbridge.io",
        "The host with protocol without trailing slash",
    ),


    "BRANDING_TITLE": (
        "IGL Trade Portal (beta)",
        "The text shown on the page headers"
    ),

    "IGL_CHANNELS_CONFIGURED": (
        "",
        "To what channels this installation can send documents; value example is SG,CN "
        "and if the target country not in the list then IGL message status will be 'not sent'. "
        "Comma-separated 2-letter country names without spaces and any other characters except the comma"
    ),
}


CONSTANCE_CONFIG_FIELDSETS = {
    'Open Attestation': (
        'OA_NOTARY_CONTRACT', 'OA_NOTARY_DOMAIN', 'OA_WRAP_API_URL',
        'OA_UNPROCESSED_QUEUE_URL', 'OA_UNPROCESSED_BUCKET_NAME', 'OA_AWS_ACCESS_KEYS',
        'OA_VERIFY_API_URL', 'UA_BASE_HOST',
    ),
    "Node Configuration": (
        "IGL_CHANNELS_CONFIGURED",
    )
}

used = []
for fields in CONSTANCE_CONFIG_FIELDSETS.values():
    used += list(fields)

general = []
for field_name in CONSTANCE_CONFIG.keys():
    if field_name not in used:
        general.append(field_name)
del used

CONSTANCE_CONFIG_FIELDSETS['General Options'] = tuple(general)
