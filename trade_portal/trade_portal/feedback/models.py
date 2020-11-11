from django.conf import settings
from django.db import models


class FeedbackItem(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, models.SET_NULL, blank=True, null=True
    )
    email = models.EmailField(
        blank=True,
        max_length=200,
        help_text=(
            "Please enter your email address here if you wish to be contacted "
            " about your query or feedback. Do not enter your email address if "
            "you wish to remain anonymous."
        ),
    )
    contact = models.TextField(
        blank=True,
        max_length=2000,
        help_text=(
            "Please enter a phone number or other additional contact information "
            "to help us contact you about your query or feedback. Do not provide "
            "contact details if you wish to remain anonymous."
        ),
    )
    created_at = models.DateTimeField(auto_now_add=True)
    text = models.TextField(
        max_length=10000, help_text="Please enter your query or feedback here."
    )

    class Meta:
        ordering = ("-created_at",)
