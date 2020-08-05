import logging

from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.views.generic import CreateView

from trade_portal.users.forms import RoleRequestForm

logger = logging.getLogger(__name__)


class RoleRequestView(LoginRequiredMixin, CreateView):
    form_class = RoleRequestForm
    template_name = "users/role-request.html"

    def get_form_kwargs(self):
        kw = super().get_form_kwargs()
        kw["user"] = self.request.user
        return kw

    def get_success_url(self):
        messages.success(
            self.request,
            "The role request has been placed; "
            "It typically takes 2 workings days to review it"
        )
        return reverse('users:detail')
