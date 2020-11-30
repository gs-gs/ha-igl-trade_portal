from django.conf import settings
from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic import TemplateView

from trade_portal.documents.models import Document, Party


class MonitoringIndexView(UserPassesTestMixin, TemplateView):
    template_name = "monitoring/index.html"

    def test_func(self):
        return self.request.user.is_staff

    def get_context_data(self, *args, **kwargs):
        c = super().get_context_data(*args, **kwargs)
        c["total_documents_issued"] = Document.objects.filter(
            workflow_status=Document.WORKFLOW_STATUS_ISSUED,
        ).count()
        c["total_documents_draft"] = Document.objects.filter(
            workflow_status=Document.WORKFLOW_STATUS_DRAFT,
        ).count()
        c["total_parties"] = Party.objects.filter(
            country=settings.ICL_TRADE_PORTAL_COUNTRY
        ).count()
        return c
