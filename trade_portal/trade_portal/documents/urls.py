from django.urls import path

from trade_portal.documents.views.documents_create import (
    DocumentCreateView,
    DocumentFillView,
    DocumentIssueView,
)
from trade_portal.documents.views.documents import (
    DocumentListView,
    DocumentDetailView,
    DocumentLogsView,
    DocumentFileDownloadView,
    DocumentHistoryFileDownloadView,
    ConsignmentUpdateView,
)
from trade_portal.legi.views import AbnLookupView, NameLookupView

app_name = "documents"

urlpatterns = [
    # Documents
    path("", view=DocumentListView.as_view(), name="list"),
    path("create-<str:dtype>/", view=DocumentCreateView.as_view(), name="create"),
    path(
        "create-<str:dtype>/<uuid:oa>/",
        view=DocumentCreateView.as_view(),
        name="create-specific",
    ),
    path("<uuid:pk>/fill/", view=DocumentFillView.as_view(), name="fill"),
    path("<uuid:pk>/issue/", view=DocumentIssueView.as_view(), name="issue"),
    path("<uuid:pk>/", view=DocumentDetailView.as_view(), name="detail"),
    path("<uuid:pk>/logs/", view=DocumentLogsView.as_view(), name="logs"),
    path(
        "<uuid:pk>/consignment-update/",
        view=ConsignmentUpdateView.as_view(),
        name="consignment-update",
    ),
    path(
        "<uuid:pk>/documents/<uuid:file_pk>/",
        view=DocumentFileDownloadView.as_view(),
        name="file-download",
    ),
    path(
        "<uuid:pk>/documents/oa/",
        view=DocumentFileDownloadView.as_view(doc_type="oa"),
        name="oa-download",
    ),
    path(
        "<uuid:pk>/documents/pdf/",
        view=DocumentFileDownloadView.as_view(doc_type="pdf"),
        name="pdf-download",
    ),
    path(
        "<uuid:pk>/historyfile/<int:history_item_id>/",
        view=DocumentHistoryFileDownloadView.as_view(),
        name="history-file-download",
    ),
    # misc
    path("api/abn-lookup/", AbnLookupView.as_view(), name="abn-lookup"),
    path("api/name-lookup/", NameLookupView.as_view(), name="name-lookup"),
]
