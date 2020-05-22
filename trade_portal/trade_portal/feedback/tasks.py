import logging

from constance import config
from config import celery_app
from django.conf import settings
from django.core.mail import send_mail

from .models import FeedbackItem

logger = logging.getLogger(__name__)


@celery_app.task()
def send_feedback_notification(fb_id):
    feedback = FeedbackItem.objects.get(pk=fb_id)
    logger.info("Sending feedback notification %s to the admin email", fb_id)
    if not config.FEEDBACK_EMAIL:
        logger.warning(
            "There was a feedback received, but the email to notify about it "
            "is not configured - FEEDBACK_EMAIL in the constance config. "
            "You still can review the feedback item in the admin panel."
        )
        return

    email_text = [
        "Text: " + feedback.text.strip(),
        "User: " + str(feedback.user.id if feedback.user else "Anon"),
        "Email: " + feedback.email.strip() or "(not filled)",
        "Contact: " + feedback.contact.strip() or "(not filled)",
        "Submitted at: " + str(feedback.created_at),
    ]
    email_text = "\n".join(email_text)

    send_mail(
        "A feedback item has been received",
        f"{email_text}\n\nYou can review it in the admin panel.",
        settings.DEFAULT_FROM_EMAIL,
        recipient_list=[config.FEEDBACK_EMAIL],
        fail_silently=False
    )
    return
