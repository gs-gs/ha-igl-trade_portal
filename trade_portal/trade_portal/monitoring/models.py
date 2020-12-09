from django.db import models, transaction
from django.contrib.postgres.fields import JSONField


class VerificationAttempt(models.Model):
    """
    The log object to be aggregated; we save the fact of verification
    with some details but they are not personal
    """

    TYPE_FILE = "file"
    TYPE_QR = "QR"
    TYPE_LINK = "link"

    TYPES = (
        (TYPE_FILE, "File"),
        (TYPE_QR, "QR"),
        (TYPE_LINK, "Direct link"),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    type = models.CharField(max_length=10, choices=TYPES)
    geo_info = JSONField(
        default=dict,
        blank=True,
    )
    document = models.ForeignKey(
        "documents.Document", models.CASCADE, blank=True, null=True
    )

    class Meta:
        ordering = ("-created_at",)

    @classmethod
    def create_from_request(cls, request, type: str):
        from trade_portal.monitoring.tasks import resolve_geoloc_ip
        c = cls(
            type=type,
        )
        c.save()
        xff = request.META.get('HTTP_X_FORWARDED_FOR')
        remote_addr = request.META.get('REMOTE_ADDR')
        remote_ip = ''.join(xff.split()) if xff else remote_addr
        transaction.on_commit(
            lambda: resolve_geoloc_ip.delay(c.pk, remote_ip)
        )
        return c


class Metric(models.Model):
    name = models.CharField(max_length=128, db_index=True)
    value = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.name} = {self.value}"
