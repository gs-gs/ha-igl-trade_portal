from django.contrib import messages
from django.views.generic import CreateView

from .forms import FeedbackForm


class FeedbackView(CreateView):
    template_name = "feedback.html"
    form_class = FeedbackForm

    def get_form_kwargs(self, *args, **kwargs):
        kw = super().get_form_kwargs(*args, **kwargs)
        kw["user"] = self.request.user if self.request.user.is_authenticated else None
        return kw

    def get_success_url(self):
        messages.success(
            self.request,
            "Thanks for your feedback! We have received it."
        )
        return "/"
