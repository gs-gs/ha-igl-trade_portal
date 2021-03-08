from django.core.management.base import BaseCommand

from trade_portal.documents.services.notarize import NotaryService


class Command(BaseCommand):
    help = "Notarize some random file"

    def handle(self, *args, **kwargs):
        file_content = (
            "a b c"  # it will probably be useful if we read that file content
        )
        NotaryService().notarize_file("xxxfile", file_content)
