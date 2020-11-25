import logging

from django.apps import AppConfig

logger = logging.getLogger(__name__)


class WebSubReceiverAppConfig(AppConfig):

    name = "trade_portal.websub_receiver"
    verbose_name = "WebSub Receiver module"
