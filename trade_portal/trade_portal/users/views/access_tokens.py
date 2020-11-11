import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView
from django.utils.translation import gettext as _
from django.shortcuts import redirect

from trade_portal.users.forms import TokenCreateForm
from trade_portal.users.models import OrganisationAuthToken

logger = logging.getLogger(__name__)


class TokensListView(LoginRequiredMixin, ListView):
    """
    Display all tokens for all organistaions which user is part of
    (but limiting to the current one). Including tokens from other users.
    """

    template_name = "users/tokens/list.html"

    def get(self, *args, **kwargs):
        current_org = self.request.user.get_current_org(self.request.session)
        if not current_org:
            messages.warning(
                self.request,
                _("Please select current organisation before managing its tokens"),
            )
            return redirect("users:detail")
        return super().get(*args, **kwargs)

    def post(self, *args, **kwargs):
        current_org = self.request.user.get_current_org(self.request.session)
        if not current_org:
            messages.warning(
                self.request,
                _("Please select current organisation before managing its tokens"),
            )
            return redirect("users:detail")
        return super().post(*args, **kwargs)

    def get_queryset(self):
        current_org = self.request.user.get_current_org(self.request.session)
        qs = OrganisationAuthToken.objects.filter(org=current_org)
        return qs


class TokenIssueView(LoginRequiredMixin, CreateView):
    form_class = TokenCreateForm
    template_name = "users/tokens/create.html"
    just_issued_token = None

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["user"] = self.request.user
        kw["current_org"] = self.request.user.get_current_org(self.request.session)
        return kw

    def get_context_data(self, *args, **kwargs):
        c = super().get_context_data(*args, **kwargs)
        c["just_issued_token"] = self.just_issued_token
        return c

    def get(self, request, *args, **kwargs):
        request.session["can_create_token"] = True
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        # self.issued_token = self._issue_token()
        # normal workflow of Django form processing
        form = self.get_form()
        if form.is_valid():
            # we must have GET request before having POST requst for same user.
            # allows us to avoid F5 problem - user needs to visit confirmation page again
            # to issue new token.
            if not request.session.get("can_create_token"):
                return redirect("users:tokens-issue")
            request.session["can_create_token"] = False
            self.form_valid(form)
            self.just_issued_token = self.object
        else:
            return self.form_invalid(form)

        return super().get(request, *args, **kwargs)

    def get_success_url(self):
        # never used but is called
        return None
