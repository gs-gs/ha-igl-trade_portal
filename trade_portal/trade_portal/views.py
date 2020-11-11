from django.conf import settings

from django.views.generic import View, TemplateView
from django.shortcuts import redirect
from mozilla_django_oidc.views import OIDCLogoutView


class HomeView(TemplateView):
    template_name = "pages/home.html"


class VerificationView(TemplateView):
    template_name = "pages/verification.html"

    def get_context_data(self, *args, **kwargs):
        c = super().get_context_data(*args, **kwargs)
        c["verification_url"] = settings.VERIFICATION_URL
        return c


class LogoutInitiateView(View):
    def get(self, request, *args, **kwargs):
        next_url = (
            ("https" if request.is_secure() else "http")
            + "://"
            + request.get_host()
            + "/logout"
        )
        return redirect(
            settings.OIDC_OP_LOGOUT_ENDPOINT
            + "?client_id="
            + settings.OIDC_RP_CLIENT_ID
            + "&logout_uri="
            + next_url
        )


class LogoutPerformView(OIDCLogoutView):
    def get(self, *args, **kwargs):
        return super().post(*args, **kwargs)
