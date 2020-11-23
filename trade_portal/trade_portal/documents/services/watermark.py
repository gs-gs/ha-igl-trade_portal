"""
Things related to the CoO packaging and sending to the upstream
"""
import io
import logging

from constance import config
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from trade_portal.documents.models import (
    Document,
    DocumentFile,
)

logger = logging.getLogger(__name__)


class WatermarkService:
    """
    Helper to add QR code to the uploaded PDF file assuming it doesn't have any
    """

    def watermark_document(self, document: Document, force: bool = False):
        qrcode_image = document.oa.get_qr_image()

        qset = document.files.all()
        if force is False:
            qset = qset.filter(is_watermarked=False)

        for docfile in qset:
            if docfile.filename.lower().endswith(".pdf"):
                self.add_watermark(docfile, qrcode_image)
        return

    def add_watermark(self, docfile: DocumentFile, qrcode_image) -> None:
        """
        Draws given QR code over a PDF content in the top right cornder
        and re-saves the file in place with updated result
        """
        # Local imports are used in case this functionality is disabled
        # for some setups/envs
        import PIL
        from reportlab.pdfgen import canvas
        from reportlab.lib.utils import ImageReader
        from reportlab.lib.units import mm
        from reportlab.lib.pagesizes import A4
        from PyPDF2 import PdfFileWriter, PdfFileReader

        logging.info("Adding a watermark for %s", docfile)
        qrcode_image = PIL.Image.open(io.BytesIO(qrcode_image))

        # Prepare the PDF document containing only QR code
        qrcode_stream = io.BytesIO()
        c = canvas.Canvas(qrcode_stream, pagesize=A4)

        x_loc = float(docfile.doc.extra_data.get("qr_x_position") or 83) / 100
        y_loc = 1 - float(docfile.doc.extra_data.get("qr_y_position") or 4) / 100

        if x_loc < 0:
            x_loc = 0
        if x_loc > 100:
            x_loc = 100
        if y_loc < 0:
            y_loc = 0
        if y_loc > 100:
            y_loc = 100

        image_width = config.QR_CODE_SIZE_MM * mm

        image_x_loc = A4[0] * x_loc
        image_y_loc = A4[1] * y_loc - image_width

        c.drawImage(
            ImageReader(qrcode_image),
            image_x_loc,
            image_y_loc,
            width=image_width,
            height=image_width,
            preserveAspectRatio=1,
        )
        c.save()

        qrcode_stream.seek(0)
        qrcode_doc = PdfFileReader(qrcode_stream)
        orig_doc = PdfFileReader(docfile.original_file or docfile.file)
        output_file = PdfFileWriter()

        for page_number in range(orig_doc.getNumPages()):
            input_page = orig_doc.getPage(page_number)
            if page_number == 0:
                # only for the first page
                input_page.mergePage(qrcode_doc.getPage(0))
            output_file.addPage(input_page)

        outputStream = io.BytesIO()
        output_file.write(outputStream)

        old_filename_parts = docfile.file.name.rsplit(".", maxsplit=1)
        new_filename = ".".join(
            [old_filename_parts[0].rstrip(".altered"), "altered", old_filename_parts[1]]
        )
        outputStream.seek(0)
        new_saved_filename = default_storage.save(
            new_filename, ContentFile(outputStream.read())
        )
        docfile.file = new_saved_filename
        logger.info("Saved altered PDF file as %s", new_saved_filename)
        docfile.is_watermarked = True
        docfile.save()
        return

    def get_first_page_as_png(self, source, page_number=0):
        import PyPDF2
        from wand.image import Image

        resolution = 140
        source = PyPDF2.PdfFileReader(source)
        dst_pdf = PyPDF2.PdfFileWriter()
        dst_pdf.addPage(source.getPage(page_number))

        pdf_bytes = io.BytesIO()
        dst_pdf.write(pdf_bytes)
        pdf_bytes.seek(0)
        img = Image(file=pdf_bytes, resolution=resolution)
        img.convert("png")
        img.format = "png"
        stream = io.BytesIO()
        img.save(file=stream)
        stream.seek(0)
        return stream
