"""
Base settings to build other settings files upon.
"""
import datetime
import environ
from django.utils.translation import gettext_lazy as _

from . import Env

ROOT_DIR = (
    environ.Path(__file__) - 3
)  # (trade_portal/config/settings/base.py - 3 = trade_portal/)
APPS_DIR = ROOT_DIR.path("trade_portal")

env = Env()

# GENERAL
ICL_TRADE_PORTAL_COUNTRY = env(
    'ICL_TRADE_PORTAL_COUNTRY',
    default=env("ICL_COUNTRY", default="AU")
)
DEBUG = env.bool("DJANGO_DEBUG", False)
IS_LAMBDA_DEPLOYMENT = env.bool('ICL_IS_LAMBDA', default=False)

TIME_ZONE = env("IGL_TIMEZONE", default="Australia/Sydney")
LANGUAGE_CODE = "en-us"
LANGUAGE_COOKIE_NAME = f"tr{ICL_TRADE_PORTAL_COUNTRY}lang"

LANGUAGES = [
    ('en', _('English')),
    ('ja', _('Japaneese')),
]

SITE_ID = 1
USE_I18N = True
USE_L10N = False
USE_TZ = True
LOCALE_PATHS = [ROOT_DIR.path("locale")]

BASE_URL = env(
    "ICL_APP_HOST",
    default=env("ICL_TRADE_PORTAL_HOST", default="http://localhost:8050")  # most preferred
)  # no trailing slash

# DATABASES
DATABASES = {"default": env.db("DATABASE_URL")}
DATABASES["default"]["ATOMIC_REQUESTS"] = True

# URLS
ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

# APPS
# ------------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "django.contrib.admin",
    "django.forms",
]
THIRD_PARTY_APPS = [
    "crispy_forms",
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "rest_framework",
    "storages",
    "dj_pagination",
    "widget_tweaks",
    "constance",
    "constance.backends.database",
    "django_tables2",
    # "django_amazon_translate",
    "siteblocks",
]

LOCAL_APPS = [
    "trade_portal.users.apps.UsersConfig",
    "trade_portal.documents",
    "trade_portal.websub_receiver.apps.WebSubReceiverAppConfig",
    "trade_portal",
]
INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS
CRISPY_TEMPLATE_PACK = "bootstrap4"
MIGRATION_MODULES = {"sites": "trade_portal.contrib.sites.migrations"}

# PASSWORDS
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher",
    "django.contrib.auth.hashers.BCryptSHA256PasswordHasher",
]

if not DEBUG:
    AUTH_PASSWORD_VALIDATORS = [
        {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
        {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
        {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
        {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    ]
else:
    AUTH_PASSWORD_VALIDATORS = []

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.common.BrokenLinkEmailsMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "dj_pagination.middleware.PaginationMiddleware",
]

# TEMPLATES
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [str(APPS_DIR.path("templates"))],
        "OPTIONS": {
            "loaders": [
                "django.template.loaders.filesystem.Loader",
                "django.template.loaders.app_directories.Loader",
            ],
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.template.context_processors.i18n",
                "django.template.context_processors.media",
                "django.template.context_processors.static",
                "django.template.context_processors.tz",
                "django.contrib.messages.context_processors.messages",
                "trade_portal.utils.context_processors.settings_context",
            ],
        },
    }
]

FORM_RENDERER = "django.forms.renderers.TemplatesSetting"

FIXTURE_DIRS = (str(APPS_DIR.path("fixtures")),)

# SECURITY
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = "DENY"

# ADMIN
ADMIN_URL = "admin/"
ADMINS = []
MANAGERS = ADMINS


# STATIC
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'
STATIC_ROOT = "/staticfiles"
STATIC_URL = "/static/"
STATICFILES_DIRS = [str(APPS_DIR.path("static"))]
STATICFILES_FINDERS = [
    "django.contrib.staticfiles.finders.FileSystemFinder",
    "django.contrib.staticfiles.finders.AppDirectoriesFinder",
]

# MEDIA
MEDIA_ROOT = str(APPS_DIR("media"))
MEDIA_URL = "/media/"


# Celery
if USE_TZ:
    CELERY_TIMEZONE = TIME_ZONE
CELERY_BROKER_URL = env("CELERY_BROKER_URL", default=None)  # empty only for collectstatic
CELERY_RESULT_BACKEND = CELERY_BROKER_URL
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TASK_TIME_LIMIT = 5 * 60
CELERY_TASK_SOFT_TIME_LIMIT = 60


CELERY_BEAT_SCHEDULE = {
    'subscribe_to_new_messages': {
        'task': 'trade_portal.websub_receiver.tasks.subscribe_to_new_messages',
        'schedule': datetime.timedelta(minutes=30),
    },
}

DEFAULT_FROM_EMAIL = env(
    "DJANGO_DEFAULT_FROM_EMAIL", default="Trade Portal <noreply@example.com>"
)
SERVER_EMAIL = env("DJANGO_SERVER_EMAIL", default=DEFAULT_FROM_EMAIL)
EMAIL_SUBJECT_PREFIX = env(
    "DJANGO_EMAIL_SUBJECT_PREFIX", default="[trade-portal]"
)

# Statd monitoring (if enabled)
STATSD_HOST = env('MON_STATSD_HOST', default=None)
if STATSD_HOST:
    STATSD_PREFIX = env('MON_STATSD_PREFIX', default='tradeportal')
    STATSD_PORT = int(env('MON_STATSD_PORT', default=8125))


BUILD_REFERENCE = env('BUILD_REFERENCE', default=None)
CONFIGURATION_REFERENCE = env('CONFIGURATION_REFERENCE', default=None)
APP_REFERENCE = env('APP_REFERENCE', default=None)

DATE_INPUT_FORMATS = [
    '%Y-%m-%d', '%d/%m/%Y', '%d/%m/%y',
    '%b %d %Y', '%b %d, %Y',            # 'Oct 25 2006', 'Oct 25, 2006'
    '%d %b %Y', '%d %b, %Y',            # '25 Oct 2006', '25 Oct, 2006'
    '%B %d %Y', '%B %d, %Y',            # 'October 25 2006', 'October 25, 2006'
    '%d %B %Y', '%d %B, %Y',            # '25 October 2006', '25 October, 2006'
]

from .base_auth import *  # NOQA
from .base_app import *  # NOQA
from .base_apis import *  # NOQA
from .base_cache import *  # NOQA
from .base_constance import *  # NOQA
from .base_logging import *  # NOQA
from .base_storages import *  # NOQA
