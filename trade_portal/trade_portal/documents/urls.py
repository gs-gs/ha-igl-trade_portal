from django.urls import path

from trade_portal.documents.views.documents import (
    DocumentListView, DocumentCreateView,
    DocumentDetailView, DocumentLogsView,
    DocumentFileDownloadView, DocumentHistoryFileDownloadView,
)
from trade_portal.documents.views.parties import (
    PartiesListView, PartyDetailView,
    PartyCreateView, PartyUpdateView,
)
from trade_portal.legi.views import AbnLookupView

app_name = "documents"

urlpatterns = [
    # Documents
    path("", view=DocumentListView.as_view(), name="list"),
    path("create-<str:dtype>/<uuid:oa>/", view=DocumentCreateView.as_view(), name="create-specific"),
    path("create-<str:dtype>/", view=DocumentCreateView.as_view(), name="create"),
    path("<uuid:pk>/", view=DocumentDetailView.as_view(), name="detail"),
    path("<uuid:pk>/logs/", view=DocumentLogsView.as_view(), name="logs"),
    # path("<uuid:pk>/update/", view=DocumentUpdateView.as_view(), name="update"),
    path(
        "<uuid:pk>/documents/<uuid:file_pk>/",
        view=DocumentFileDownloadView.as_view(),
        name="file-download"
    ),
    path(
        "<uuid:pk>/historyfile/<int:history_item_id>/",
        view=DocumentHistoryFileDownloadView.as_view(),
        name="history-file-download"
    ),

    # Related objects - Parties
    path("parties/", view=PartiesListView.as_view(), name="parties"),
    path("parties/create/", view=PartyCreateView.as_view(), name="party-create"),
    path("parties/<int:pk>/", view=PartyDetailView.as_view(), name="party-detail"),
    path("parties/<int:pk>/update/", view=PartyUpdateView.as_view(), name="party-update"),

    # misc
    path('api/abn-lookup/', AbnLookupView.as_view(), name='abn-lookup'),
]
