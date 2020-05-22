from captcha.fields import ReCaptchaField
from captcha.widgets import ReCaptchaV3
from constance import config
from django import forms

from .models import FeedbackItem
from .tasks import send_feedback_notification


class FeedbackForm(forms.ModelForm):
    captcha = ReCaptchaField(widget=ReCaptchaV3)

    class Meta:
        model = FeedbackItem
        fields = [
            'text', 'email', 'contact',
        ]

    def __init__(self, user, *args, **kwargs):
        self.user = user
        if config.ENABLE_CAPTCHA:
            self.Meta.fields.append("captcha")
        super().__init__(*args, **kwargs)
        if not config.ENABLE_CAPTCHA:
            del self.fields["captcha"]
        if self.user:
            self.fields["email"].initial = user.email
            self.fields["contact"].initial = "\n".join([
                f"{user.first_name} {user.last_name}".strip() or user.username,
            ])

    def save(self, *args, **kwargs):
        self.instance.user = self.user
        super().save(*args, **kwargs)
        send_feedback_notification.apply_async(
            [self.instance.pk],
            countdown=3
        )
