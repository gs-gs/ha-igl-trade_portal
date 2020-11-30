from django.urls import path

from trade_portal.monitoring.views import MonitoringIndexView

app_name = "monitoring"
urlpatterns = [
    path("", view=MonitoringIndexView.as_view(), name="index"),
]
