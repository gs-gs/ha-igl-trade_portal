"""
Things related to the CoO packaging and sending to the upstream
"""
import io
import logging
import time

from constance import config
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from trade_portal.documents.models import (
    Document,
    DocumentFile,
    DocumentHistoryItem,
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
                t0 = time.time()
                self.add_watermark(docfile, qrcode_image)
                time_spent = round(time.time() - t0, 4)  # seconds
                DocumentHistoryItem.objects.create(
                    is_error=False,
                    type="message",
                    document=document,
                    message=f"QR code applied to the PDF document in {time_spent}s",
                    object_body=str(docfile),
                )
        return

    def get_document_filesize(self, docfile: DocumentFile) -> (int, int):
        """
        Return x, y tuple meaning the original page size (mm)
        Or -1, -1 if the document is encrypted (which doesn't mean it can't be read, but can't be updated)
        Or 0, 0 if the document can't be parsed (not a PDF or some internal format issue)
        """
        from PyPDF2 import PdfFileReader
        from reportlab.lib.units import mm

        try:
            # Read the original PDF first to detemine it's page size (the first page)
            orig_doc = PdfFileReader(docfile.original_file or docfile.file)
            orig_doc_first_page_size = orig_doc.getPage(0).mediaBox
        except Exception as e:
            if "file has not been decrypted" in str(e):
                return -1, -1
            else:
                logger.exception(e)
                return 0, 0
        return (
            round(
                float(orig_doc_first_page_size[2] - orig_doc_first_page_size[0]) / mm,
                2
            ),
            round(
                float(orig_doc_first_page_size[3] - orig_doc_first_page_size[1]) / mm,
                2
            )
        )

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
        from PyPDF2 import PdfFileWriter, PdfFileReader

        logging.info("Adding a watermark for %s", docfile)
        qrcode_image = PIL.Image.open(io.BytesIO(qrcode_image))

        # Read the original PDF first to detemine it's page size (the first page)
        orig_doc = PdfFileReader(docfile.original_file or docfile.file)
        orig_doc_first_page_size = orig_doc.getPage(0).mediaBox

        orig_doc_pagesize = (
            float(orig_doc_first_page_size[2] - orig_doc_first_page_size[0]),
            float(orig_doc_first_page_size[3] - orig_doc_first_page_size[1]),
        )

        # Prepare the PDF document containing only QR code
        qrcode_stream = io.BytesIO()
        c = canvas.Canvas(qrcode_stream, pagesize=orig_doc_pagesize)

        x_loc = float(docfile.doc.extra_data.get("qr_x_position") or 83) / 100.0
        y_loc = 1 - float(docfile.doc.extra_data.get("qr_y_position") or 4) / 100.0

        if x_loc < 0:
            x_loc = 0
        if x_loc > 100:
            x_loc = 100
        if y_loc < 0:
            y_loc = 0
        if y_loc > 100:
            y_loc = 100

        image_width = config.QR_CODE_SIZE_MM * mm
        image_x_loc = orig_doc_pagesize[0] * x_loc
        image_y_loc = orig_doc_pagesize[1] * y_loc - image_width

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

    def get_first_page_as_png(self, *args, **kwargs):
        return self.get_first_page_as_pdf2image(*args, **kwargs)

    def get_first_page_as_pdf2image(self, source, page_number=0):
        """
        Uses opencv library and works better with encrypted/protected PDFs
        """
        import tempfile
        import cv2
        from pdf2image import convert_from_bytes

        images = convert_from_bytes(source.read())

        png_content = None
        with tempfile.NamedTemporaryFile(suffix=".ppm") as incoming_ppm_image:
            with tempfile.NamedTemporaryFile(suffix=".png") as tmp_png_file:
                images[0].save(incoming_ppm_image.name)
                cv2.imwrite(tmp_png_file.name, cv2.imread(incoming_ppm_image.name))
                png_content = open(tmp_png_file.name, "rb").read()
        return png_content

    def get_first_page_as_png_wand(self, source, page_number=0):
        """
        Doesn't work well with encrypted PDFs, even if printing is allowed so
        nothing stops us from rendering it to PNG
        """
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
