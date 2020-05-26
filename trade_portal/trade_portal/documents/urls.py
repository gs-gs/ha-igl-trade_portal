from django.urls import path

from trade_portal.documents.views.documents import (
    DocumentListView, DocumentCreateView,
    DocumentDetailView, DocumentUpdateView,
    DocumentFileDownloadView,
)
from trade_portal.documents.views.parties import (
    PartiesListView, PartyDetailView,
    PartyCreateView, PartyUpdateView,
)

app_name = "documents"

urlpatterns = [
    # Documents
    path("", view=DocumentListView.as_view(), name="list"),
    path("create/", view=DocumentCreateView.as_view(), name="create"),
    path("<uuid:pk>/", view=DocumentDetailView.as_view(), name="detail"),
    path("<uuid:pk>/update/", view=DocumentUpdateView.as_view(), name="update"),
    path(
        "<uuid:pk>/documents/<uuid:file_pk>/",
        view=DocumentFileDownloadView.as_view(),
        name="file-download"
    ),

    # Related objects - Parties
    path("parties/", view=PartiesListView.as_view(), name="parties"),
    path("parties/create/", view=PartyCreateView.as_view(), name="party-create"),
    path("parties/<int:pk>/", view=PartyDetailView.as_view(), name="party-detail"),
    path("parties/<int:pk>/update/", view=PartyUpdateView.as_view(), name="party-update"),
]
