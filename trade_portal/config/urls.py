# from allauth.account.views import logout
from django.conf import settings
from django.urls import include, path
from django.conf.urls.static import static
from django.contrib import admin
from django.views import defaults as default_views
from django.views.generic import TemplateView

from trade_portal.feedback.views import FeedbackView
from trade_portal.views import (
    HomeView, VerificationView, LogoutInitiateView, LogoutPerformView,
)
from trade_portal.documents.views.oa import OaCyphertextRetrieve

from .healthcheck import HealthcheckView

urlpatterns = [
    path("", HomeView.as_view(), name="home"),
    path("about/", TemplateView.as_view(template_name="pages/about.html")),
    path("verification/", VerificationView.as_view()),

    path("documents/", include("trade_portal.documents.urls", namespace="documents")),
    path(
        "api/documents/v0/",
        include("trade_portal.document_api.urls", namespace="document-api-v0")
    ),
    path("v/", include("trade_portal.oa_verify.urls", namespace="oa-verify")),
    path("oa/<str:key>/", OaCyphertextRetrieve.as_view(), name="oa-cyphertext-retrieve"),
    path("profile/", include("trade_portal.users.urls", namespace="users")),
    path("feedback/", FeedbackView.as_view(), name="feedback"),
    path("websub/", include("trade_portal.websub_receiver.urls", namespace="websub")),

    path("healthcheck", HealthcheckView.as_view()),

    path("accounts/", include("allauth.urls")),
    path("oidc/logout-initiate", LogoutInitiateView.as_view(), name="logout_initiate"),
    path("logout/", LogoutPerformView.as_view(), name="logout"),
    path("oidc/", include('mozilla_django_oidc.urls')),

    path('i18n/', include('django.conf.urls.i18n')),

    path(settings.ADMIN_URL, admin.site.urls),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

if settings.DEBUG:
    # This allows the error pages to be debugged during development, just visit
    # these url in browser to see how these error pages look like.
    urlpatterns += [
        path(
            "400/",
            default_views.bad_request,
            kwargs={"exception": Exception("Bad Request!")},
        ),
        path(
            "403/",
            default_views.permission_denied,
            kwargs={"exception": Exception("Permission Denied")},
        ),
        path(
            "404/",
            default_views.page_not_found,
            kwargs={"exception": Exception("Page not Found")},
        ),
        path("500/", default_views.server_error),
    ]
    if "debug_toolbar" in settings.INSTALLED_APPS:
        import debug_toolbar

        urlpatterns = [path("__debug__/", include(debug_toolbar.urls))] + urlpatterns
