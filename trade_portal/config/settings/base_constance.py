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
}
