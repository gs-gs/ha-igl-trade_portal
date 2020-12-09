from django.contrib.auth.signals import user_logged_in, user_login_failed
from django.db.models import F
from django.dispatch import receiver


@receiver(user_logged_in)
def user_logged_in_callback(sender, request, user, **kwargs):
    from trade_portal.monitoring.models import Metric
    Metric.objects.get_or_create(name="logins_number_success")
    Metric.objects.filter(name="logins_number_success").update(
        value=F('value') + 1
    )


@receiver(user_login_failed)
def user_login_failed_callback(sender, credentials, **kwargs):
    from trade_portal.monitoring.models import Metric
    Metric.objects.get_or_create(name="logins_number_failed")
    Metric.objects.filter(name="logins_number_failed").update(
        value=F('value') + 1
    )
