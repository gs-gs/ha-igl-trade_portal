from django.conf.urls import url, include
# from django.urls import path
from rest_framework import routers

from trade_portal.document_api.views import (
    CertificateViewSet,
)

router = routers.DefaultRouter()
router.register(r'certificate', CertificateViewSet)

app_name = "document-api-v0"
urlpatterns = [
    url(r'^', include(router.urls)),
]
