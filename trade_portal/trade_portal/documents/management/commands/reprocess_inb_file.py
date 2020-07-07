from django.core.management.base import BaseCommand

from trade_portal.documents.tasks import process_incoming_document_received


class Command(BaseCommand):
    help = 'Run the processing of a document again'

    def add_arguments(self, parser):
        parser.add_argument('doc_id', type=str)

    def handle(self, *args, **kwargs):
        process_incoming_document_received(kwargs["doc_id"])
