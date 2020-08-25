from django.urls import path

from trade_portal.oa_verify.views import OaVerificationView

app_name = "oa_verify"

urlpatterns = [
    # Documents
    path("", view=OaVerificationView.as_view(), name="verification"),
]
