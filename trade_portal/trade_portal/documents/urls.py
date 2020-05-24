from django.urls import path

from trade_portal.documents.views.documents import (
    DocumentListView, DocumentCreateView,
    DocumentDetailView, DocumentUpdateView,
    DocumentFileDownloadView,
)

app_name = "documents"

urlpatterns = [
    path("", view=DocumentListView.as_view(), name="list"),
    path("create/", view=DocumentCreateView.as_view(), name="create"),
    path("<uuid:pk>/", view=DocumentDetailView.as_view(), name="detail"),
    path("<uuid:pk>/update/", view=DocumentUpdateView.as_view(), name="update"),
    path(
        "<uuid:pk>/documents/<uuid:file_pk>/",
        view=DocumentFileDownloadView.as_view(),
        name="file-download"
    ),
]
