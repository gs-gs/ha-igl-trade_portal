from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin as Login, AccessMixin
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.http import HttpResponse, Http404
from django.shortcuts import redirect
from django.views.generic import (
    DetailView, ListView, CreateView, UpdateView,
)
from django_tables2 import SingleTableView
from django.urls import reverse


from trade_portal.documents.forms import (
    DocumentCreateForm,
)
from trade_portal.documents.models import Document
from trade_portal.documents.tables import DocumentsTable
from trade_portal.documents.tasks import lodge_document
from trade_portal.utils.monitoring import statsd_timer


class DocumentQuerysetMixin(AccessMixin):

    def get_queryset(self):
        qs = Document.objects.all()
        user = self.request.user
        # filter by the current org
        # (this assumes that current org is definitely available by the user)
        qs = qs.filter(
            created_by_org=user.get_current_org(self.request.session)
        ).select_related(
            "issuer", "exporter"
        )
        return qs

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if not request.user.is_staff:
            if not request.user.orgs:
                messages.warning(
                    request,
                    "You are not a member of any organisation - which is "
                    "mandatory to access the documents page"
                )
                return redirect('users:detail')
        return super().dispatch(request, *args, **kwargs)


class DocumentListView(Login, DocumentQuerysetMixin, SingleTableView, ListView):
    template_name = 'documents/list.html'
    model = Document
    table_class = DocumentsTable
    table_pagination = {
        "per_page": 15,
    }

    @statsd_timer("view.DocumentListView.dispatch")
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_queryset(self):
        qs = super().get_queryset()
        # TODO: implement start and end date after the date format is updated
        status_filter = self.request.GET.get("status_filter", "").strip() or None
        if status_filter:
            qs = qs.filter(
                status=status_filter
            )
        type_filter = self.request.GET.get("type_filter", "").strip() or None
        if type_filter:
            qs = qs.filter(
                type=type_filter
            )
        exporter_filter = self.request.GET.get("exporter_filter", "").strip() or None
        if exporter_filter:
            qs = qs.filter(
                Q(exporter__business_id__icontains=exporter_filter) |
                Q(exporter__name__icontains=exporter_filter) |
                Q(exporter__dot_separated_id__icontains=exporter_filter)
            )
        importer_filter = self.request.GET.get("importer_filter", "").strip() or None
        if importer_filter:
            qs = qs.filter(
                importer_name__icontains=importer_filter
            )

        q = self.request.GET.get("q", "").strip() or None
        if q:
            qs = qs.filter(search_field__icontains=q)
        return qs

    def get_context_data(self, *args, **kwargs):
        c = super().get_context_data(*args, **kwargs)
        c["Document"] = Document
        return c


class DocumentCreateView(Login, CreateView):
    template_name = 'documents/create.html'
    form_class = DocumentCreateForm

    @statsd_timer("view.DocumentCreateView.dispatch")
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_form_kwargs(self):
        k = super().get_form_kwargs()
        k['user'] = self.request.user
        k['current_org'] = self.request.user.get_current_org(self.request.session)
        return k

    def get_success_url(self):
        messages.success(
            self.request,
            "The document you have just created will be notarised and will be sent "
            "to the importing country via the inter-government ledger."
        )
        return reverse('documents:detail', args=[self.object.pk])


# class DocumentUpdateView(Login, DocumentQuerysetMixin, UpdateView):
#     template_name = 'documents/update.html'
#     form_class = DocumentUpdateForm

#     @statsd_timer("view.DocumentUpdateView.dispatch")
#     def dispatch(self, *args, **kwargs):
#         return super().dispatch(*args, **kwargs)

#     def get_form_kwargs(self):
#         k = super().get_form_kwargs()
#         k['user'] = self.request.user
#         k['current_org'] = self.request.user.get_current_org(self.request.session)
#         return k

#     def get_success_url(self):
#         messages.success(
#             self.request,
#             "The document has been updated"
#         )
#         return reverse('documents:detail', args=[self.object.pk])


class DocumentDetailView(Login, DetailView):
    template_name = 'documents/detail.html'
    model = Document


class DocumentLogsView(Login, DetailView):
    template_name = 'documents/logs.html'
    model = Document


class DocumentFileDownloadView(Login, DocumentQuerysetMixin, DetailView):

    def get_object(self):
        try:
            c = self.get_queryset().get(pk=self.kwargs['pk'])
            doc = c.files.get(id=self.kwargs['file_pk'])
        except ObjectDoesNotExist:
            raise Http404()
        return doc

    def get(self, *args, **kwargs):
        # standard file approach
        document = self.get_object()
        response = HttpResponse(document.file, content_type='application/octet-stream')
        response['Content-Disposition'] = 'attachment; filename="%s"' % document.file.name
        return response
