from django.conf.urls import url, include
from django.urls import path
from django.views.generic import TemplateView
from rest_framework import routers

from trade_portal.document_api.views import (
    CertificateViewSet, CertificateFileView, CertificateIssueView,
)

router = routers.DefaultRouter()
router.register(r'CertificatesOfOrigin', CertificateViewSet)

app_name = "document-api-v0"

urlpatterns = [
    path("", TemplateView.as_view(template_name="document_api/swagger_container.html"), name="swagger"),
    url(r'^', include(router.urls)),
    path("CertificatesOfOrigin/<uuid:pk>/attachment/", CertificateFileView.as_view(), name="attachment"),
    path("CertificatesOfOrigin/<uuid:pk>/issue/", CertificateIssueView.as_view(), name="issue")
]
