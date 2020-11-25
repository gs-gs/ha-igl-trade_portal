import os
from celery import Celery
from celery.signals import beat_init

# set the default Django settings module for the 'celery' program.
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")

app = Celery("trade_portal")

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django app configs.
app.autodiscover_tasks()


@beat_init.connect()
def on_startup_subscribe(conf=None, **kwargs):
    from trade_portal.websub_receiver.tasks import subscribe_to_new_messages
    subscribe_to_new_messages.delay()
