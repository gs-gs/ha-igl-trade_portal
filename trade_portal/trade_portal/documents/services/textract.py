import logging
import tempfile
import json

import camelot

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
    def extract_docfile(cls, docfile):
        with tempfile.NamedTemporaryFile(suffix=".pdf") as infile:
            infile.write(docfile.file.read())
            infile.flush()
            tables = camelot.read_pdf(infile.name)

        with tempfile.NamedTemporaryFile(suffix=".json") as outfile:
            tables[0].to_json(outfile.name)
            outfile.seek(0)
            json_tables = json.loads(outfile.read())

        metadata = {}

        for row in json_tables:
            for col_index, cell_content in row.items():
                if cell_content.strip():
                    cell_lines = cell_content.splitlines()
                    if len(cell_lines) > 1:
                        title, content = cell_lines[0].strip(), "\n".join(cell_lines[1:]).strip()
                    else:
                        title = cell_lines[0]
                        content = "(none)"
                    metadata[title] = content

        return metadata
