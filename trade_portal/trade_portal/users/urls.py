from django.urls import path

from trade_portal.users.views import (
    user_update_view,
    user_detail_view,
)

app_name = "users"
urlpatterns = [
    path("", view=user_detail_view, name="detail"),
    path("update/", view=user_update_view, name="update"),

]
