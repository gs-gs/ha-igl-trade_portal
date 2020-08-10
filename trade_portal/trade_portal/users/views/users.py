import logging

from django.core.exceptions import ValidationError
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import (
    DetailView, RedirectView, UpdateView, View
)
from django.shortcuts import redirect
from django.urls import reverse

from trade_portal.users.models import Organisation, OrgRoleRequest
from trade_portal.users.forms import UserChangeForm

logger = logging.getLogger(__name__)
User = get_user_model()


class UserDetailView(LoginRequiredMixin, DetailView):

    def get_object(self):
        return self.request.user

    def post(self, request, *args, **kwargs):
        from trade_portal.users.tasks import notify_staff_about_evidence_uploaded
        if "evidence" in request.FILES:
            for validator in OrgRoleRequest._meta.get_field("evidence").validators:
                try:
                    validator(request.FILES["evidence"])
                except ValidationError as e:
                    messages.warning(request, e.messages[0])
                    return redirect(request.path_info)

            req = OrgRoleRequest.objects.get(
                pk=request.POST.get("request_id"),
                created_by=request.user,
                status__in=[
                    OrgRoleRequest.STATUS_EVIDENCE,
                    OrgRoleRequest.STATUS_REQUESTED
                ]
            )
            req.evidence = request.FILES["evidence"]
            if req.status == OrgRoleRequest.STATUS_EVIDENCE:
                req.status = OrgRoleRequest.STATUS_REQUESTED
                notify_staff_about_evidence_uploaded.apply_async(
                    [req.id],
                    countdown=1
                )
            req.save()
            messages.success(
                request,
                "The file has been uploaded as an evidence and the request has been sent to review"
            )
        return redirect(request.path_info)


user_detail_view = UserDetailView.as_view()


class UserUpdateView(LoginRequiredMixin, UpdateView):
    form_class = UserChangeForm

    def get_success_url(self):
        return reverse("users:detail")

    def get_object(self):
        return User.objects.get(pk=self.request.user.pk)

    def form_valid(self, form):
        messages.info(
            self.request, "Your profile has been updated successfully"
        )
        return super().form_valid(form)


user_update_view = UserUpdateView.as_view()


class UserRedirectView(LoginRequiredMixin, RedirectView):

    permanent = False

    def get_redirect_url(self):
        return reverse("users:detail")


user_redirect_view = UserRedirectView.as_view()


class ChangeOrgView(LoginRequiredMixin, View):
    def post(self, request, *args, **kwargs):
        new_org_id = request.POST.get("current_org")
        next_url = request.GET.get("next") or request.POST.get("next") or "/"
        if not next_url.startswith("/"):
            raise Exception("Incorrect next url")

        if request.user.is_staff:
            # no need to check the permissions for that org
            org = Organisation.objects.get(pk=new_org_id)
        else:
            org_ms = request.user.orgmembership_set.all().filter(
                org_id=new_org_id
            ).first()

            if not org_ms:
                messages.error(request, "You don't have access to that org anymore")
                return redirect(next_url)
            org = org_ms.org

        request.session["current_org_id"] = int(org.pk)
        messages.success(request, f"The {org} has been selected as the current organisation")
        return redirect(next_url)
