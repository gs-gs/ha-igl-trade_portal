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
from django.utils.translation import gettext as _


from trade_portal.documents.forms import (
    DocumentCreateForm, DraftDocumentUpdateForm, ConsignmentSectionUpdateForm,
)
from trade_portal.documents.models import Document, OaDetails, DocumentFile
from trade_portal.documents.tables import DocumentsTable
from trade_portal.documents.tasks import lodge_document
from trade_portal.utils.monitoring import statsd_timer


class DocumentQuerysetMixin(AccessMixin):

    def get_queryset(self):
        qs = Document.objects.all()
        user = self.request.user
        current_org = user.get_current_org(self.request.session)
        if current_org.is_regulator:
            # regulator can see everything
            pass
        elif current_org.is_chambers:
            # chambers can see only their own documents
            qs = qs.filter(
                created_by_org=current_org
            )
        elif current_org.is_trader:
            qs = qs.filter(
                importer_name__in=(
                    current_org.name,
                    current_org.business_id,
                )
            ) | qs.filter(
                exporter__clear_business_id=current_org.business_id
            ).exclude(
                exporter__clear_business_id=""
            ) | qs.filter(
                exporter__name=current_org.name
            ).exclude(
                exporter__name=""
            )
        else:
            qs = Document.objects.none()

        qs = qs.select_related(
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
                    _(
                        "You are not a member of any organisation - which is "
                        "mandatory to access the documents page"
                    )
                )
                return redirect('users:detail')
        return super().dispatch(request, *args, **kwargs)


class DocumentListView(Login, DocumentQuerysetMixin, SingleTableView, ListView):
    template_name = 'documents/list.html'
    model = Document
    table_class = DocumentsTable
    table_pagination = {
        "per_page": 25,
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
        if not self.request.user.is_authenticated:
            return self.handle_no_permission()
        current_org = self.request.user.get_current_org(self.request.session)
        if not current_org.is_chambers:
            messages.error(self.request, _("Only chambers can create new documents"))
            return redirect('/documents/')
        return super().dispatch(*args, **kwargs)

    def get(self, *args, **kwargs):
        # auth mixin is already applied here - no need to think about it
        # if there is no "oa-pk" kwarg then we must create some oa credential
        # and redirect user to the creation page for this specific one - so the QR
        # code is shown
        if not self.kwargs.get('oa'):
            oa = OaDetails.retrieve_new(
                for_org=self.request.user.get_current_org(self.request.session)
            )
            return redirect(
                'documents:create-specific',
                dtype=self.kwargs['dtype'], oa=oa.pk
            )
        return super().get(*args, **kwargs)

    def get_form_kwargs(self):
        k = super().get_form_kwargs()
        current_org = self.request.user.get_current_org(self.request.session)
        k['dtype'] = self.kwargs['dtype']
        k['oa'] = OaDetails.objects.get(
            pk=self.kwargs['oa'],
            created_for=current_org
        )
        k['user'] = self.request.user
        k['current_org'] = current_org
        return k

    def get_success_url(self):
        return reverse('documents:issue', args=[self.object.pk])


class DocumentDetailView(Login, DocumentQuerysetMixin, DetailView):
    template_name = 'documents/detail.html'
    model = Document

    def get(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.workflow_status == Document.WORKFLOW_STATUS_DRAFT:
            # this is draft statement, show user the step2 submission
            # page in all cases
            return redirect(
                'documents:issue', obj.pk
            )
        return super().get(request, *args, **kwargs)


class DocumentIssueView(Login, DocumentQuerysetMixin, DetailView):
    template_name = 'documents/issue.html'
    model = Document

    def get(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.workflow_status != Document.WORKFLOW_STATUS_DRAFT:
            return redirect(
                'documents:detail', obj.pk
            )
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.workflow_status != Document.WORKFLOW_STATUS_DRAFT:
            return redirect(
                'documents:detail', obj.pk
            )
        if "issue" in request.POST:
            messages.success(
                self.request,
                _(
                    "The document you have just created will be notarised and will be sent "
                    "to the importing country via the Secure Trade Lane."
                )
            )
            lodge_document.apply_async(
                [obj.pk],
                countdown=2
            )

        return redirect("documents:detail", obj.pk)


class DocumentUpdateView(Login, DocumentQuerysetMixin, UpdateView):
    # Only for 'draft' status
    template_name = 'documents/update.html'
    form_class = DraftDocumentUpdateForm

    def dispatch(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return self.handle_no_permission()
        # we don't check for document visibility because it's done by mixin
        current_org = self.request.user.get_current_org(self.request.session)
        if not current_org.is_chambers and not current_org.is_trader:
            messages.error(
                self.request,
                _("Only chambers and trade party can update these details")
            )
            return redirect('/documents/')
        return super().dispatch(*args, **kwargs)

    def get_form_kwargs(self):
        k = super().get_form_kwargs()
        current_org = self.request.user.get_current_org(self.request.session)
        k['user'] = self.request.user
        k['current_org'] = current_org
        return k

    def get_success_url(self):
        messages.success(
            self.request,
            _("The document details have been updated")
        )
        return reverse('documents:issue', args=[self.object.pk])


class DocumentLogsView(Login, DocumentQuerysetMixin, DetailView):
    template_name = 'documents/logs.html'
    model = Document


class DocumentFileDownloadView(Login, DocumentQuerysetMixin, DetailView):
    doc_type = "file"

    def get_object(self):
        try:
            c = self.get_queryset().get(pk=self.kwargs['pk'])
            if "file_pk" in self.kwargs:
                doc = c.files.get(id=self.kwargs['file_pk'])
            elif self.doc_type == "oa":
                doc = c.get_vc()
            elif self.doc_type == "pdf":
                first_pdf = c.files.filter(filename__endswith=".pdf").first()
                if not first_pdf:
                    first_pdf = c.files.all().first()
                return first_pdf
        except ObjectDoesNotExist:
            raise Http404()
        return doc

    def get(self, *args, **kwargs):
        # standard file approach
        document = self.get_object()
        if isinstance(document, DocumentFile):
            content_type = (
                "application/pdf"
                if document.filename.lower().endswith(".pdf")
                else 'application/octet-stream'
            )
            response = HttpResponse(document.file, content_type=content_type)
            if not self.request.GET.get('inline'):
                response['Content-Disposition'] = 'attachment; filename="%s"' % document.filename
        elif document is None:
            raise Http404()
        elif self.doc_type == "oa":
            # OA document from the OA details object
            response = HttpResponse(document, content_type='application/json')
            response['Content-Disposition'] = 'attachment; filename=OA.json'
        else:
            raise Exception("Unkown document type")
        return response


class DocumentHistoryFileDownloadView(Login, DocumentQuerysetMixin, DetailView):

    def get_object(self):
        try:
            c = self.get_queryset().get(pk=self.kwargs['pk'])
            historyitem = c.history.get(id=self.kwargs['history_item_id'])
            if not historyitem.related_file:
                raise ObjectDoesNotExist()
        except ObjectDoesNotExist:
            raise Http404()
        return historyitem

    def get(self, *args, **kwargs):
        # standard file approach
        historyitem = self.get_object()
        response = HttpResponse(historyitem.related_file, content_type='application/octet-stream')
        response['Content-Disposition'] = 'attachment; filename="%s"' % historyitem.related_file.name
        return response


class ConsignmentUpdateView(Login, DocumentQuerysetMixin, UpdateView):
    template_name = 'documents/consignment-update.html'
    form_class = ConsignmentSectionUpdateForm

    def dispatch(self, *args, **kwargs):
        # we don't check for document visibility because it's done by mixin
        current_org = self.request.user.get_current_org(self.request.session)
        if not current_org.is_chambers and not current_org.is_trader:
            messages.error(
                self.request,
                _("Only chambers and trade party can update these details")
            )
            return redirect('/documents/')
        return super().dispatch(*args, **kwargs)

    def get_success_url(self):
        messages.success(
            self.request,
            _("The consignment details have been saved successfully")
        )
        return reverse('documents:detail', args=[self.object.pk])
