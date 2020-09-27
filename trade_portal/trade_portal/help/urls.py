from django.urls import path

from django.views.generic import TemplateView

app_name = "help"

urlpatterns = [
    path("", TemplateView.as_view(template_name="help/home.html")),
    path("register/", TemplateView.as_view(template_name="help/register.html")),
    path("api/", TemplateView.as_view(template_name="help/api.html")),
]
