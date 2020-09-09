from django.urls import path

from trade_portal.users.views.access_tokens import (
    TokensListView, TokenIssueView,
)
from trade_portal.users.views.orgs import (
    RoleRequestView,
)
from trade_portal.users.views.management import (
    PendingUsersView, RolesRequestsView, EvidenceDownloadView,
)
from trade_portal.users.views.users import (
    user_update_view, user_detail_view, ChangeOrgView,
)

app_name = "users"
urlpatterns = [
    path("", view=user_detail_view, name="detail"),
    path("update/", view=user_update_view, name="update"),
    path("change-org/", ChangeOrgView.as_view(), name="change-org"),

    path("access-tokens/", TokensListView.as_view(), name="tokens-list"),
    path("access-tokens/issue/", TokenIssueView.as_view(), name="tokens-issue"),

    path("role-request/", RoleRequestView.as_view(), name="role-request"),
    path(
        "role-request/<int:pk>/evidence-download/",
        EvidenceDownloadView.as_view(),
        name="evidence-download"
    ),

    # admin section
    path("pending/", PendingUsersView.as_view(), name="pending"),
    path("roles-requests/", RolesRequestsView.as_view(), name="roles-requests"),
]
