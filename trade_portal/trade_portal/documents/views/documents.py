from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin as Login
from django.views.generic import (
    DetailView, ListView, CreateView, UpdateView,
)
from django.core.exceptions import ObjectDoesNotExist
from django.http import HttpResponse, Http404
from django.urls import reverse
from django.shortcuts import redirect

from trade_portal.documents.forms import (
    DocumentCreateForm, DocumentUpdateForm,
)
from trade_portal.documents.models import Document
from trade_portal.utils.monitoring import statsd_timer


class DocumentQuerysetMixin(object):

    def get_queryset(self):
        qs = Document.objects.all()
        user = self.request.user
        if user.is_staff:
            # no further checks for the staff members
            return qs
        return qs.filter(
            created_by=user
            # TODO: or available to the user's ABN
        )


class DocumentListView(Login, DocumentQuerysetMixin, ListView):
    template_name = 'documents/list.html'
    model = Document

    @statsd_timer("view.DocumentListView.dispatch")
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)


class DocumentCreateView(Login, CreateView):
    template_name = 'documents/create.html'
    form_class = DocumentCreateForm

    @statsd_timer("view.DocumentCreateView.dispatch")
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_form_kwargs(self):
        k = super().get_form_kwargs()
        k['user'] = self.request.user
        return k

    def get_success_url(self):
        messages.success(
            self.request,
            "The draft document has been created. You may continue filling it with"
            " the data now"
        )
        return reverse('documents:detail', args=[self.object.pk])


class DocumentUpdateView(Login, DocumentQuerysetMixin, UpdateView):
    template_name = 'documents/update.html'
    form_class = DocumentUpdateForm

    @statsd_timer("view.DocumentUpdateView.dispatch")
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    def get_form_kwargs(self):
        k = super().get_form_kwargs()
        k['user'] = self.request.user
        return k

    def get_success_url(self):
        messages.success(
            self.request,
            "The document has been updated"
        )
        return reverse('documents:detail', args=[self.object.pk])


class DocumentDetailView(Login, DetailView):
    template_name = 'documents/detail.html'
    model = Document

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        if 'lodge-document' in request.POST:
            if obj.status == Document.STATUS_COMPLETE:
                obj.lodge()
                messages.success(request, 'The document has been lodged')
                return redirect(obj.get_absolute_url())
        return redirect(request.path_info)


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
