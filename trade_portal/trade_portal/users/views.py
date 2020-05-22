import logging

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import DetailView, RedirectView, UpdateView
from django.urls import reverse

from trade_portal.users.forms import UserChangeForm

logger = logging.getLogger(__name__)
User = get_user_model()


class UserDetailView(LoginRequiredMixin, DetailView):

    def get_object(self):
        return self.request.user


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

    def post(self, request, *args, **kwargs):
        assert request.user.is_authenticated
        return super().post(request, *args, **kwargs)


user_update_view = UserUpdateView.as_view()


class UserRedirectView(LoginRequiredMixin, RedirectView):

    permanent = False

    def get_redirect_url(self):
        return reverse("users:detail")


user_redirect_view = UserRedirectView.as_view()
