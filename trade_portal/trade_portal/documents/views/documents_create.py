from constance import config
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin as Login
from django.shortcuts import redirect
from django.views.generic import (
    DetailView,
    CreateView,
    UpdateView,
)
from django.urls import reverse
from django.utils.html import mark_safe, escape
from django.utils.translation import gettext as _

from trade_portal.documents.forms import (
    DocumentCreateForm,
    DraftDocumentUpdateForm,
)
from trade_portal.documents.models import Document, OaDetails
from trade_portal.documents.tasks import lodge_document
from trade_portal.documents.views.documents import DocumentQuerysetMixin
from trade_portal.utils.monitoring import statsd_timer


class DocumentCreateView(Login, CreateView):
    template_name = "documents/create.html"
    form_class = DocumentCreateForm

    @statsd_timer("view.DocumentCreateView.dispatch")
    def dispatch(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return self.handle_no_permission()
        current_org = self.request.user.get_current_org(self.request.session)
        if not current_org.is_chambers:
            messages.error(self.request, _("Only chambers can create new documents"))
            return redirect("/documents/")
        return super().dispatch(*args, **kwargs)

    def get(self, *args, **kwargs):
        # auth mixin is already applied here - no need to think about it
        # if there is no "oa-pk" kwarg then we must create some oa credential
        # and redirect user to the creation page for this specific one - so the QR
        # code is shown
        if not self.kwargs.get("oa"):
            oa = OaDetails.retrieve_new(
                for_org=self.request.user.get_current_org(self.request.session)
            )
            return redirect(
                "documents:create-specific", dtype=self.kwargs["dtype"], oa=oa.pk
            )
        return super().get(*args, **kwargs)

    def get_form_kwargs(self):
        k = super().get_form_kwargs()
        current_org = self.request.user.get_current_org(self.request.session)
        k["dtype"] = self.kwargs["dtype"]
        k["oa"] = OaDetails.objects.get(pk=self.kwargs["oa"], created_for=current_org)
        k["user"] = self.request.user
        k["current_org"] = current_org
        return k

    def get_success_url(self):
        return reverse("documents:fill", args=[self.object.pk])


class DocumentIssueView(Login, DocumentQuerysetMixin, DetailView):
    template_name = "documents/issue.html"
    model = Document

    def get(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.workflow_status != Document.WORKFLOW_STATUS_DRAFT:
            return redirect("documents:detail", obj.pk)
        if not obj.issuer:
            # the previous step is not filled yet
            messages.success(request, "Please fill the document details")
            return redirect("documents:fill", obj.pk)
        self.obj = obj
        return super().get(request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        c = super().get_context_data(*args, **kwargs)
        c["data_warnings"] = self._get_data_warnings()
        last_issued_document = (
            self.get_queryset()
            .filter(
                created_by_org=self.request.user.get_current_org(self.request.session),
                workflow_status=Document.WORKFLOW_STATUS_ISSUED,
            )
            .order_by("-created_at")
            .first()
        )
        if last_issued_document:
            c["initial_qr_x_value"] = last_issued_document.extra_data.get(
                "qr_x_position"
            )
            c["initial_qr_y_value"] = last_issued_document.extra_data.get(
                "qr_y_position"
            )
        c["QR_CODE_SIZE_MM"] = config.QR_CODE_SIZE_MM
        c["FIRST_PAGE_PDF_WIDTH_MM"] = self.obj.get_pdf_attachment().metadata.get("width_mm") or 210
        c["FIRST_PAGE_PDF_HEIGHT_MM"] = self.obj.get_pdf_attachment().metadata.get("height_mm") or 297
        c["IS_PDF_ENCRYPTED"] = self.obj.get_pdf_attachment().metadata.get("encrypted_pdf") is True
        c["IS_PDF_UNPARSEABLE"] = self.obj.get_pdf_attachment().metadata.get("unparseable_pdf") is True
        c["SHOW_QR_CODE_ATTACHMENT"] = (
            self.obj.get_pdf_attachment().is_watermarked is False
            and not c["IS_PDF_UNPARSEABLE"]
            and not c["IS_PDF_ENCRYPTED"]
        )
        return c

    def _get_data_warnings(self):
        """
        Validates the data entered by the user vs parsed PDF content and returns warnings
        if any
        """
        warnings = {}
        obj = self.get_object()

        # warnings based on object fields
        another_document = Document.objects.filter(
            created_by_org=obj.created_by_org,
            document_number=obj.document_number,
            workflow_status__in=(
                Document.WORKFLOW_STATUS_DRAFT,
                Document.WORKFLOW_STATUS_ISSUED,
            )
        ).exclude(
            pk=obj.pk
        ).exclude(
            verification_status__in=(
                Document.V_STATUS_ERROR,
                Document.V_STATUS_FAILED,
            )
        ).first()
        if another_document:
            warnings["Document Number"] = mark_safe(
                f"There is another document "
                f"(<a href='{another_document.get_absolute_url()}'>{escape(another_document)}</a>)"
                f" with the same document number, please be careful not to issue it twice"
            )

        # warnings based on the text extraction
        raw_text = obj.extra_data.get("metadata", {}).get("raw_text")
        if raw_text:
            if obj.document_number not in raw_text:
                warnings[
                    "Document Number"
                ] = "The value hasn't been found in the statement file"
            if obj.exporter:
                if (
                    obj.exporter.name not in raw_text
                    and obj.exporter.business_id not in raw_text
                ):
                    warnings[
                        "Exporter"
                    ] = "The value hasn't been found in the statement file"
        return warnings

    def post(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.workflow_status != Document.WORKFLOW_STATUS_DRAFT:
            return redirect("documents:detail", obj.pk)
        if not obj.issuer:
            # the previous step is not filled yet
            messages.success(request, "Please fill the document details")
            return redirect("documents:fill", obj.pk)
        if "issue" in request.POST or "issue-without-qr-code" in request.POST:
            if "issue-without-qr-code" in request.POST:
                att = obj.get_pdf_attachment()
                if att:
                    # we mark it as not requiring watermarking
                    att.is_watermarked = None
                    att.save()
            obj.workflow_status = Document.WORKFLOW_STATUS_ISSUED
            obj.extra_data["qr_x_position"] = request.POST.get("qr_x")
            obj.extra_data["qr_y_position"] = request.POST.get("qr_y")
            obj.save()

            message = "The document will be issued as a Verifiable Credential (VC)"
            # and, if a direct G2G channel exists, will also be sent to the importing regulator
            messages.success(
                self.request,
                _(message),
            )
            lodge_document.apply_async([obj.pk], countdown=2)

        return redirect("documents:detail", obj.pk)


class DocumentFillView(Login, DocumentQuerysetMixin, UpdateView):
    # Only for 'draft' status
    template_name = "documents/update.html"
    form_class = DraftDocumentUpdateForm

    def dispatch(self, *args, **kwargs):
        if not self.request.user.is_authenticated:
            return self.handle_no_permission()

        obj = self.get_object()
        if obj.workflow_status != Document.WORKFLOW_STATUS_DRAFT:
            return redirect("documents:detail", obj.pk)
        # we don't check for document visibility because it's done by mixin
        current_org = self.request.user.get_current_org(self.request.session)
        if not current_org.is_chambers and not current_org.is_trader:
            messages.error(
                self.request,
                _("Only chambers and trade party can update these details"),
            )
            return redirect("/documents/")
        return super().dispatch(*args, **kwargs)

    def get_form_kwargs(self):
        k = super().get_form_kwargs()
        current_org = self.request.user.get_current_org(self.request.session)
        k["user"] = self.request.user
        k["current_org"] = current_org
        return k

    def get_success_url(self):
        messages.success(self.request, _("The document details have been updated"))
        return reverse("documents:issue", args=[self.object.pk])
