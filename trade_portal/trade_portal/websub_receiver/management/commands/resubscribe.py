from django.core.management.base import BaseCommand

from trade_portal.websub_receiver.tasks import subscribe_to_new_messages


class Command(BaseCommand):
    help = "Re-subscribe to all incoming messages from a node"

    def handle(self, *args, **kwargs):
        subscribe_to_new_messages()
