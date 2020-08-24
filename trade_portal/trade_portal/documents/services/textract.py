import io
import logging
import os
import subprocess
import tempfile

logger = logging.getLogger(__name__)


class MetadataExtractService:
    """
    apt install libgl-dev
    """

    @classmethod
    def extract(cls, doc):
        doc.extra_data["metadata"] = doc.extra_data.get("metadata", {}) or {}
        old_md = doc.extra_data["metadata"].copy()
        for docfile in doc.files.all():
            if docfile.filename.lower().endswith(".pdf"):
                md = cls.extract_docfile(docfile)
                if md:
                    doc.extra_data["metadata"].update(md)
        if old_md != doc.extra_data["metadata"]:
            doc.save()
            logger.info("The document %s metadata has been updated", doc)

    @classmethod
    def extract_docfile(cls, *args, **kwargs):
        return cls.extract_docfile_tesseract(*args, **kwargs)

    @classmethod
    def extract_docfile_tesseract(cls, docfile):
        # pdf2image pypdf2
        from pdf2image import convert_from_bytes
        from PyPDF2 import PdfFileWriter, PdfFileReader
        # import time

        # First we get only the first page of the document
        incoming_pdf = PdfFileReader(docfile.file)
        first_page_document = PdfFileWriter()
        first_page_document_file = io.BytesIO()
        first_page_document.addPage(incoming_pdf.getPage(0))
        first_page_document.write(first_page_document_file)
        first_page_document_file.seek(0)

        # convert to PNG
        with tempfile.TemporaryDirectory(prefix="ocr_data_") as tmp_dir:
            images = convert_from_bytes(
                first_page_document_file.read(),
                dpi=300,
                fmt="png",
                transparent=False,
            )
            first_image = images[0]
            first_image.convert("RGB")

            # split it to 2 vertical parts for better OCRing
            width, height = first_image.size
            # Cut the images in half
            left_part = first_image.crop((0, 0, width // 2, height))
            right_part = first_image.crop((width // 2, 0, width, height))

            # and save them
            left_part.save(tmp_dir + ".1.png", "PNG")
            right_part.save(tmp_dir + ".2.png", "PNG")

            # run Tesseract
            subprocess.run([
                "tesseract",  # base command
                tmp_dir + ".1.png",  # input filename
                tmp_dir + ".1.png",  # out prefix - tesseract will create .txt file with that name
            ])
            text1 = open(tmp_dir + ".1.png" + ".txt", "r").read()

            subprocess.run([
                "tesseract",  # base command
                tmp_dir + ".2.png",  # input filename
                tmp_dir + ".2.png",  # out prefix - tesseract will create .txt file with that name
            ])
            text2 = open(tmp_dir + ".2.png" + ".txt", "r").read()

            os.remove(tmp_dir + ".1.png")
            os.remove(tmp_dir + ".2.png")
            os.remove(tmp_dir + ".1.png.txt")
            os.remove(tmp_dir + ".2.png.txt")

        full_text = text1 + "\n\n" + text2

        md = {}
        md = {
            "raw_text": full_text,
        }
        md.update(cls.tesseract_output_to_metadata(full_text))
        return md

    @classmethod
    def tesseract_output_to_metadata(cls, raw_text):
        md = {}
        # first pass
        for line in raw_text.splitlines():
            if line.count(":") == 1:
                # may be a key-value pair
                key, value = line.split(":")
                if value.strip():
                    md[key.strip().capitalize()] = value.strip()
        # second pass
        lines_acc = []
        for line in raw_text.splitlines():
            if "|" in line:  # always block reset
                if lines_acc:
                    # new block while the prev block is present
                    if len(lines_acc) > 1:
                        md[lines_acc[0].strip()] = "\n".join(
                            lines_acc[1:]
                        ).strip()
                lines_acc = []
            if line and line[0].isdigit() and line[1] == ".":
                # may be a block start
                if lines_acc:
                    # new block while the prev block is present
                    if len(lines_acc) > 1:
                        md[lines_acc[0].strip()] = "\n".join(
                            lines_acc[1:]
                        ).strip()
                    lines_acc = [line]
                else:
                    # just start a new block
                    if line:
                        lines_acc.append(line)
            else:
                # may be a block continuation
                if lines_acc:
                    if line:
                        lines_acc.append(line)
        return md

    @classmethod
    def extract_docfile_camelot(cls, docfile):
        return {}
        # import camelot
        # with tempfile.NamedTemporaryFile(suffix=".pdf") as infile:
        #     infile.write(docfile.file.read())
        #     infile.flush()
        #     tables = camelot.read_pdf(infile.name)

        # # with tempfile.NamedTemporaryFile(suffix=".json") as outfile:
        # #     tables[0].to_json(outfile.name)
        # #     outfile.seek(0)
        # #     json_tables = json.loads(outfile.read())

        # metadata = {}

        # for table in tables:
        #     for row in table.data:
        #         for index, cell_content in enumerate(row):
        #             print(cell_content)
        #             if cell_content.strip():
        #                 cell_lines = cell_content.splitlines()
        #                 if len(cell_lines) > 1:
        #                     title, content = cell_lines[0].strip(), "\n".join(cell_lines[1:]).strip()
        #                 else:
        #                     title = cell_lines[0]
        #                     content = "(none)"
        #                 metadata[title] = content

        # return metadata
