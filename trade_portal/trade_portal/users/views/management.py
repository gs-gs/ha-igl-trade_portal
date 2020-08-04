import logging

from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import UserPassesTestMixin
from django.views.generic import (
    TemplateView,
)
from django.shortcuts import redirect

from trade_portal.users.models import Organisation, OrgMembership
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
