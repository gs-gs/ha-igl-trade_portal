import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import UserPassesTestMixin
from django.http import Http404, HttpResponse
from django.views.generic import (
    TemplateView, DetailView,
)
from django.shortcuts import redirect

from trade_portal.users.models import (
    Organisation, OrgMembership, OrgRoleRequest,
)
from trade_portal.users.tasks import update_org_fields

logger = logging.getLogger(__name__)
User = get_user_model()


class PendingUsersView(UserPassesTestMixin, TemplateView):
    template_name = "users/pending.html"

    def test_func(self):
        return self.request.user.is_superuser

    def get_context_data(self, *args, **kwargs):
        c = super().get_context_data(*args, **kwargs)
        c["pending_users"] = self._get_pending_users()
        return c

    def _get_pending_users(self):
        return User.objects.filter(
            orgmembership__isnull=True,
            is_staff=False,
            is_superuser=False,
        ).exclude(
            initial_business_id=""
        )

    def post(self, request, *args, **kwargs):
        if "add_user_to" in request.POST:
            user, org = request.POST.get("add_user_to").split("_")
            user = self._get_pending_users().get(pk=user)
            org = Organisation.objects.get(
                business_id=user.initial_business_id,
                pk=org
            )
            logger.info(
                "Adding user %s to the org %s because %s wants it",
                user, org, request.user,
            )
            OrgMembership.objects.get_or_create(  # for case of double submission
                org=org,
                user=user,
            )
            messages.success(request, f"The user has been added to {org}")
        elif "create_org_for_user" in request.POST:
            user = self._get_pending_users().get(
                pk=request.POST.get("create_org_for_user")
            )
            org, _ = Organisation.objects.get_or_create(
                # warning: we assume that the ABN is valid here and user pressing that
                # button ensured it
                business_id=user.initial_business_id,
                defaults={
                    "name": f"{settings.BID_NAME} {user.initial_business_id}",
                    "dot_separated_id": f"org.{user.initial_business_id}.{settings.BID_NAME}",
                }
            )
            update_org_fields.apply_async(
                [org.pk],
                countdown=2
            )
            OrgMembership.objects.get_or_create(  # for case of double submission
                org=org,
                user=user,
            )
            logger.info("Created organisation %s", org)
            logger.info("Access to the org %s has been given to %s", org, user)
            messages.success(
                request,
                "The organisation has been created and this user got access to it"
            )

        return redirect(request.path_info)


class RolesRequestsView(UserPassesTestMixin, TemplateView):
    template_name = "users/roles-requests.html"

    def test_func(self):
        return self.request.user.is_superuser

    def get_context_data(self, *args, **kwargs):
        c = super().get_context_data(*args, **kwargs)
        c["pending_requests"] = OrgRoleRequest.objects.filter(
            status__in=(
                OrgRoleRequest.STATUS_REQUESTED,
                OrgRoleRequest.STATUS_EVIDENCE,
            )
        )
        return c

    def post(self, request, *args, **kwargs):
        if "approve_request" in request.POST:
            req = OrgRoleRequest.objects.get(
                pk=request.POST.get("approve_request")
            )
            req.status = OrgRoleRequest.STATUS_APPROVED
            req.save()
            if req.role == req.ROLE_TRADER:
                req.org.is_trader = True
            elif req.role == req.ROLE_CHAMBERS:
                req.org.is_chambers = True
            req.org.save()
            messages.success(
                request,
                f"Role {req.get_role_display()} has been granted to the {req.org}"
            )
        elif "reject_request" in request.POST:
            req = OrgRoleRequest.objects.get(
                pk=request.POST.get("reject_request")
            )
            req.status = OrgRoleRequest.STATUS_REJECTED
            req.save()
            messages.warning(
                request,
                f"Role {req.get_role_display()} has NOT been granted to the {req.org}"
            )
        elif "evidence_required" in request.POST:
            req = OrgRoleRequest.objects.get(
                pk=request.POST.get("evidence_required")
            )
            req.status = OrgRoleRequest.STATUS_EVIDENCE
            req.save()
            messages.info(
                request,
                "The request has been marked as 'Evidence Requested' "
                "and will change it's status back once it's uploaded"
            )
        return redirect(request.path_info)


class EvidenceDownloadView(UserPassesTestMixin, DetailView):

    def test_func(self):
        return self.request.user.is_superuser

    def get_object(self):
        try:
            return OrgRoleRequest.objects.get(pk=self.kwargs["pk"])
        except OrgRoleRequest.DoesNotExist:
            raise Http404()

    def get(self, *args, **kwargs):
        # standard file approach
        req = self.get_object()
        response = HttpResponse(req.evidence, content_type='application/octet-stream')
        response['Content-Disposition'] = 'attachment; filename="%s"' % req.evidence.name
        return response
