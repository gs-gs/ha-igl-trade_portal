import logging

from django.apps import AppConfig
from django.conf import settings

logger = logging.getLogger(__name__)


class WebSubReceiverAppConfig(AppConfig):

    name = "trade_portal.websub_receiver"
    verbose_name = "WebSub Receiver module"

    def ready(self):
        is_unittest = getattr(settings, "IS_UNITTEST", False)
        is_debug = settings.DEBUG
        if is_debug and not is_unittest:
            from trade_portal.websub_receiver.tasks import subscribe_to_new_messages

            subscribe_to_new_messages()
