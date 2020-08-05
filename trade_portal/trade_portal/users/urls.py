from django.urls import path

from trade_portal.users.views.users import (
    user_update_view, user_detail_view, ChangeOrgView,
)
from trade_portal.users.views.orgs import (
    RoleRequestView,
)
from trade_portal.users.views.management import (
    PendingUsersView,
)

app_name = "users"
urlpatterns = [
    path("", view=user_detail_view, name="detail"),
    path("update/", view=user_update_view, name="update"),
    path("change-org/", ChangeOrgView.as_view(), name="change-org"),

    path("role-request/", RoleRequestView.as_view(), name="role-request"),

    # admin section
    path("pending/", PendingUsersView.as_view(), name="pending"),
]
