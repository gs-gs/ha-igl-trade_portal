from django.conf.urls import url, include
from django.urls import path
from rest_framework import routers

from trade_portal.document_api.views import (
    CertificateViewSet, CertificateFileView, CertificateIssueView,
)

router = routers.DefaultRouter()
router.register(r'CertificatesOfOrigin', CertificateViewSet)

app_name = "document-api-v0"
urlpatterns = [
    url(r'^', include(router.urls)),
    path("CertificatesOfOrigin/<uuid:pk>/attachment/", CertificateFileView.as_view(), name="attachment"),
    path("CertificatesOfOrigin/<uuid:pk>/issue/", CertificateIssueView.as_view(), name="issue")
]
