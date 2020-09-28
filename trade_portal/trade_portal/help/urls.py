from django.urls import path

from django.views.generic import TemplateView

app_name = "help"

urlpatterns = [
    path("", TemplateView.as_view(template_name="help/home.html")),
    path("register/", TemplateView.as_view(template_name="help/register.html")),
    path("roles/", TemplateView.as_view(template_name="help/roles.html")),
    path("api/", TemplateView.as_view(template_name="help/api.html")),
]
