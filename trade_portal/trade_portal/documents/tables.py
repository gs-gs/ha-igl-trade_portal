# tutorial/tables.py
import django_tables2 as tables

from .models import Document


class DocumentsTable(tables.Table):
    document_number = tables.TemplateColumn(
        verbose_name="Document No.",
        template_code="""
            <a href="{% url 'documents:detail' record.pk %}">
                {{ record.document_number|default:record.short_id }}
            </a>
        """
    )
    importing_country = tables.Column(verbose_name="Importing Country")
    consignment_details = tables.TemplateColumn(
        verbose_name='Consignment Ref.',
        template_code="""
            {{ record.consignment_ref_doc_number }}
            {{ record.consignment_ref_doc_type }}
            {{ record.consignment_ref_doc_issuer }}
            {{ record.invoice_number }}
        """,
        orderable=False,
    )
    logs_link = tables.TemplateColumn(
        verbose_name='Logs',
        template_code="""
            <a href="{% url 'documents:logs' record.pk %}">Logs</a>
        """,
        orderable=False,
    )

    class Meta:
        model = Document
        template_name = "tables_bt4.html"
        fields = (
            "document_number", "type", "status", "sending_jurisdiction", "importing_country",
            "created_at", "issuer", "exporter", "importer_name",
            "consignment_details", "logs_link",
        )
