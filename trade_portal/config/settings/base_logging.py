# https://docs.python.org/3.6/library/logging.html
import logging

import sentry_sdk
from sentry_sdk.integrations.django import DjangoIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
from sentry_sdk.integrations.celery import CeleryIntegration

from .base import env


LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s [%(asctime)s] %(name)s %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
    },
    'handlers': {
        'console': {
            'level': 'INFO',
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        '': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': True,
        },
        'elasticsearch': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': True,
        },
        'boto3': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },

        'celery': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'celery.beat': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'celery.worker.strategy': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'celery.worker.job': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },

        'botocore': {
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        'rq.worker': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'django.security.DisallowedHost': {
            # boring to have it in sentry
            'handlers': ['console'],
            'level': 'CRITICAL',
            'propagate': False,
        },
        'django.request': {
            # boring to have warnings in sentry as well
            'handlers': ['console'],
            'level': 'CRITICAL',
            'propagate': False,
        },
        'pdfminer': {
            # boring to have warnings in sentry as well
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },

        # should be configured to pass messages to some secure storage
        'audit': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}


SENTRY_DSN = env("SENTRY_DSN", default=None)
if SENTRY_DSN:
    SENTRY_LOG_LEVEL = env.int("DJANGO_SENTRY_LOG_LEVEL", logging.INFO)

    sentry_logging = LoggingIntegration(
        level=SENTRY_LOG_LEVEL,
        event_level=logging.WARNING,
    )
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[sentry_logging, DjangoIntegration(), CeleryIntegration()],
    )
