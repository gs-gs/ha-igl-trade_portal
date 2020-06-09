from .base import *  # noqa
from .base import env

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

DUMB_ABR_REQUESTS = True
CELERY_TASK_ALWAYS_EAGER = True

IS_UNITTEST = True

DUMB_ABR_REQUESTS = True
