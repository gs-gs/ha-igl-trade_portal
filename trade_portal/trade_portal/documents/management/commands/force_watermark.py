from django.core.management.base import BaseCommand

from trade_portal.documents.models import Document
from trade_portal.documents.services.watermark import WatermarkService


class Command(BaseCommand):
    help = "Run the watermarking for document even if it wasn't requested"

    def add_arguments(self, parser):
        parser.add_argument("doc_id", type=str)

    def handle(self, *args, **kwargs):
        doc = Document.objects.get(pk=kwargs["doc_id"])
        WatermarkService().watermark_document(doc)
