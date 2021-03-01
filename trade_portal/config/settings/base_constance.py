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
    "USERS_NOTIFICATIONS_MAILBOX": (
        "",
        "The email where new notifications about registered users/etc will be sent",
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
    "QR_CODE_SIZE_MM": (
        26,
        "The size (millimeters) of QR code to watermark over PDFs we generate"
    ),
    "VERIFIER_SHOW_DOWNLOAD_TAB": (
        True,
        "Uncheck that if we don't need to display 'Download PDF' and 'Download OA' buttons for the verifier"
    )
}


CONSTANCE_CONFIG_FIELDSETS = {
    "Node Configuration": (
        "IGL_CHANNELS_CONFIGURED",
    ),
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
