from django.conf import settings
from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic import TemplateView

from trade_portal.documents.models import Document, Party
from trade_portal.monitoring.models import VerificationAttempt, Metric
from trade_portal.users.models import User, Organisation


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
        c["total_documents_failed"] = Document.objects.filter(
            verification_status=Document.V_STATUS_FAILED,
        ).count()
        c["total_documents_validated"] = Document.objects.filter(
            verification_status=Document.V_STATUS_VALID,
        ).count()

        c["total_parties"] = Party.objects.filter(
            country=settings.ICL_TRADE_PORTAL_COUNTRY
        ).count()
        c['verifications_file'] = VerificationAttempt.objects.filter(
            type=VerificationAttempt.TYPE_FILE
        ).count()
        c['verifications_qr'] = VerificationAttempt.objects.filter(
            type=VerificationAttempt.TYPE_QR
        ).count()
        c['verifications_link'] = VerificationAttempt.objects.filter(
            type=VerificationAttempt.TYPE_LINK
        ).count()
        c["base_metrics"] = self._get_base_metrics()
        return c

    def _get_base_metrics(self):
        logins_number_success = Metric.objects.filter(name="logins_number_success").first()
        logins_number_success = logins_number_success.value if logins_number_success else 0
        logins_number_failed = Metric.objects.filter(name="logins_number_failed").first()
        logins_number_failed = logins_number_failed.value if logins_number_failed else 0

        return {
            "number_of_orgs": Organisation.objects.count(),
            "number_of_users": User.objects.count(),
            "logins_number_success": logins_number_success,
            "logins_number_failed": logins_number_failed,
        }
