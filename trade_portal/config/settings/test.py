from .base import *  # noqa
from .base import env, HAYSTACK_CONNECTIONS

SECRET_KEY = env(
    "DJANGO_SECRET_KEY",
    default="pJIZUZWYcRiERZZhLGN1ev9zqp5v1bxTASXPuJ96EjYnOHjRukIVsGQZVfwhbbSn",
)
TEST_RUNNER = "django.test.runner.DiscoverRunner"
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

TEMPLATES[-1]["OPTIONS"]["loaders"] = [  # type: ignore[index] # noqa F405
    (
        "django.template.loaders.cached.Loader",
        [
            "django.template.loaders.filesystem.Loader",
            "django.template.loaders.app_directories.Loader",
        ],
    )
]

EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

HAYSTACK_CONNECTIONS['default']['INDEX_NAME'] += "_test"
HAYSTACK_SIGNAL_PROCESSOR = 'haystack.signals.RealtimeSignalProcessor'

DUMB_ABR_REQUESTS = True
CELERY_TASK_ALWAYS_EAGER = True

HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.simple_backend.SimpleEngine',
    },
}

IS_UNITTEST = True
