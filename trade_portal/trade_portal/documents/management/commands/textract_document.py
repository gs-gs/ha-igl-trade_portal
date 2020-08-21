from django.core.management.base import BaseCommand

from trade_portal.documents.services.textract import MetadataExtractService
from trade_portal.documents.models import Document


class Command(BaseCommand):
    help = 'Extracting metadata from the document'

    def add_arguments(self, parser):
        parser.add_argument('doc_id', type=str)

    def handle(self, *args, **kwargs):
        doc = Document.objects.get(pk=kwargs["doc_id"])
        MetadataExtractService.extract(doc)
