from django.urls import path

from trade_portal.documents.views.documents import (
    DocumentListView, DocumentCreateView,
    DocumentDetailView, DocumentLogsView,
    DocumentFileDownloadView, DocumentHistoryFileDownloadView,
    ConsignmentUpdateView,
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
    path("<uuid:pk>/consignment-update/", view=ConsignmentUpdateView.as_view(), name="consignment-update"),
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

    # misc
    path('api/abn-lookup/', AbnLookupView.as_view(), name='abn-lookup'),
]
