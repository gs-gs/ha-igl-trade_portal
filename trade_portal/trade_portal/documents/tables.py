# tutorial/tables.py
import django_tables2 as tables
from django.utils.translation import gettext_lazy as _

from .models import Document


class DocumentsTable(tables.Table):
    document_number = tables.TemplateColumn(
        verbose_name=_("Document\nNo."),
        template_code="""
            <a href="{% url 'documents:detail' record.pk %}">
                {{ record.document_number|default:record.short_id }}
            </a>
        """
    )
    sending_jurisdiction = tables.Column(verbose_name=_("Sending\nJurisdiction"))
    importing_country = tables.Column(verbose_name=_("Importing\nCountry"))
    type = tables.Column(verbose_name=_("Document\nType"))
    issuer = tables.TemplateColumn(
        template_code="""{{ record.issuer.name }}"""
    )
    exporter = tables.TemplateColumn(
        template_code="""{{ record.exporter.name }}"""
    )
    importer_name = tables.Column(
        verbose_name=_("Importer\nName")
    )
    workflow_status = tables.Column(
        verbose_name=_("Workflow\nStatus")
    )
    verification_status = tables.TemplateColumn(
        verbose_name=_("Verfication\nStatus"),
        template_code="""
        {% if record.verification_status == 'valid' %}
          <span class='badge badge-success'>{{ record.get_verification_status_display }}</span>
        {% else %}
          {% if record.verification_status == 'failed' or record.verification_status == 'error' %}
            <span class='badge badge-danger'>{{ record.get_verification_status_display }}</span>
          {% else %}
            <span class='badge badge-primary'>{{ record.get_verification_status_display }}</span>
          {% endif %}
        {% endif %}
        """
    )
    status = tables.TemplateColumn(
        verbose_name=_("IGL\nStatus"),
        template_code="""
        {% if record.status == 'not-sent' %}
            <span class='badge badge-default'>Not Sent</span>
        {% endif %}
        {% if record.status == 'pending' %}
            <span class='badge badge-warning'>{{ record.get_status_display }}</span>
        {% endif %}
        {% if record.status == 'validated' %}
            <span class='badge badge-success'>{{ record.get_status_display }}</span>
        {% endif %}
        {% if record.status == 'failed' %}
            <span class='badge badge-danger'>{{ record.get_status_display }}</span>
        {% endif %}
        {% if record.status == 'incoming' %}
            <span class='badge badge-primary'>{{ record.get_status_display }}</span>
        {% endif %}
        """
    )
    consignment_details = tables.TemplateColumn(
        verbose_name=_('Consignment\nRef.'),
        template_code="""
            {{ record.consignment_ref_doc_number }}
        """,
        orderable=False,
    )
    logs_link = tables.TemplateColumn(
        verbose_name=_('Logs'),
        template_code="""
            <a href="{% url 'documents:logs' record.pk %}">Logs</a>
        """,
        orderable=False,
    )

    class Meta:
        model = Document
        template_name = "tables_bt4.html"
        fields = (
            "document_number", "type", "workflow_status", "verification_status", "status",
            "sending_jurisdiction", "importing_country",
            "created_at", "issuer", "exporter", "importer_name",
            "consignment_details", "logs_link",
        )
