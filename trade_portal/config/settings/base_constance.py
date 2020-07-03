from . import Env
env = Env()

CONSTANCE_BACKEND = 'constance.backends.database.DatabaseBackend'

CONSTANCE_CONFIG = {
    'ENABLE_CAPTCHA': (
        True,
        "Use Google ReCaptchav3; disable for legal or debug/hotfix reasons"
    ),
    'FEEDBACK_EMAIL': (
        "",
        "Where to send the feedback notifications to"
    ),
    'OA_NOTARY_CONTRACT': (
        '0xa57812DeC86336809Ea68987AbaA1669DeA31541',
        'Please configure this value so notarization works correctly'
    ),
    'OA_WRAP_API_URL': (
        'http://docker-host:9090',
        'Either local or remote setup which is able to wrap documents'
    )
}
