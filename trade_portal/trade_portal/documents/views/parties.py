from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin as Login, AccessMixin
from django.views.generic import (
    DetailView, ListView, CreateView, UpdateView,
)
from django.urls import reverse
from django.shortcuts import redirect

from trade_portal.documents.forms import (
    PartyCreateForm, PartyUpdateForm,
)
from trade_portal.documents.models import Party


class PartiesQuerysetMixin(AccessMixin):

    def get_queryset(self):
        qs = Party.objects.all()
        user = self.request.user
        # filter by the current org
        qs = qs.filter(
            created_by_org=user.get_current_org(self.request.session)
        )
        return qs

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return self.handle_no_permission()

        if not request.user.orgs:
            messages.warning(
                request,
                "You are not a member of any organisation - which is "
                "mandatory to access the documents page"
            )
            return redirect('users:detail')
        return super().dispatch(request, *args, **kwargs)


class PartiesListView(Login, PartiesQuerysetMixin, ListView):
    template_name = 'parties/list.html'
    model = Party


class PartyCreateView(Login, CreateView):
    template_name = 'parties/create.html'
    form_class = PartyCreateForm

    def get_form_kwargs(self):
        k = super().get_form_kwargs()
        k['user'] = self.request.user
        k['current_org'] = self.request.user.get_current_org(self.request.session)
        return k

    def get_success_url(self):
        messages.success(
            self.request,
            "The party has been added to the system and is ready to be assigned "
            "to the documents."
        )
        return reverse('documents:party-detail', args=[self.object.pk])


class PartyUpdateView(Login, PartiesQuerysetMixin, UpdateView):
    template_name = 'parties/update.html'
    form_class = PartyUpdateForm

    def get_form_kwargs(self):
        k = super().get_form_kwargs()
        k['user'] = self.request.user
        k['current_org'] = self.request.user.get_current_org(self.request.session)
        return k

    def get_success_url(self):
        messages.success(
            self.request,
            "The party information has been changed"
        )
        return reverse('documents:party-detail', args=[self.object.pk])


class PartyDetailView(Login, DetailView):
    template_name = 'parties/detail.html'
    model = Party
