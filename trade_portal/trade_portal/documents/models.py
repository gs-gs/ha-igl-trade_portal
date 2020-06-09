import random
import mimetypes
import string
import logging
import uuid
from base64 import b64encode

from django.conf import settings
from django.contrib.postgres.fields import JSONField
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django_countries.fields import CountryField

# from intergov_client.predicates import Predicates

from trade_portal.utils.qr import get_qrcode_image
from trade_portal.utils.monitoring import statsd_timer

logger = logging.getLogger(__name__)


class FTA(models.Model):
    # the Free Trading Agreement, per multiple countries (but may be just 2 of them)
    name = models.CharField(max_length=256, blank=True, default='')
    country = CountryField(multiple=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ('name',)
        verbose_name = "FTA"
        verbose_name_plural = "FTAs"


class Party(models.Model):
    # This is business field, just a dictionary of values to click on
    # and bears no access right meaning (apart of business ID, which
    # gives access to organisations owning it)
    TYPE_EXPORTER = 'e'
    TYPE_IMPORTER = 'i'
    TYPE_CHAMBERS = 'c'
    TYPE_OTHER = 'o'

    TYPE_CHOICES = (
        (TYPE_EXPORTER, "Exporter"),
        (TYPE_IMPORTER, "Importer"),
        (TYPE_CHAMBERS, "Chambers"),
        (TYPE_OTHER, "Other"),
    )

    created_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, models.SET_NULL,
        related_name="parties_created",
        blank=True, null=True)
    created_by_org = models.ForeignKey(
        "users.Organisation", models.SET_NULL,
        related_name="parties",
        blank=True, null=True
    )

    # exporter or importer
    type = models.CharField(max_length=1, blank=True, choices=TYPE_CHOICES, default=TYPE_OTHER)
    business_id = models.CharField(max_length=256, help_text="Abn for example", blank=True)
    name = models.CharField(max_length=256, blank=True)
    country = CountryField(blank=True)

    def __str__(self):
        return f"{self.name} {self.business_id} {self.country}".strip()

    class Meta:
        ordering = ('name',)
        verbose_name_plural = "parties"


class Document(models.Model):
    # Business status
    STATUS_DRAFT = 'draft'
    STATUS_SUBMITTED = 'submitted'
    STATUS_ISSUED = 'issued'
    STATUS_NOT_ISSUED = 'not-issued'
    STATUS_ACCEPTED = 'accepted'
    STATUS_DISPUTED = 'disputed'
    STATUS_EXPIRED = 'expired'
    STATUS_ACQUITTED = 'acquitted'
    STATUS_REJECTED = 'rejected'
    # some error, mostly the internal one
    STATUS_ERROR = 'error'

    STATUS_CHOICES = (
        (STATUS_DRAFT, 'Draft'),
        (STATUS_SUBMITTED, 'Submitted'),
        (STATUS_ISSUED, 'Issued'),
        (STATUS_NOT_ISSUED, 'Not issued'),
        (STATUS_ACCEPTED, 'Accepted'),
        (STATUS_DISPUTED, 'Disputed'),
        (STATUS_REJECTED, 'Rejected'),
        (STATUS_ACQUITTED, 'Acquitted'),
        (STATUS_EXPIRED, 'Expired'),
        (STATUS_ERROR, 'Error'),
    )

    TYPE_PREF_COO = "pref_coo"
    TYPE_NONPREF_COO = "non_pref_coo"

    TYPE_CHOICES = (
        (TYPE_PREF_COO, "Preferential Certificate of Origin"),
        (TYPE_NONPREF_COO, "Non-preferential Certificate of Origin"),
    )

    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    type = models.CharField(max_length=64, choices=TYPE_CHOICES)

    created_at = models.DateTimeField(default=timezone.now)
    created_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, models.SET_NULL,
        blank=True, null=True)
    created_by_org = models.ForeignKey(
        "users.Organisation", models.SET_NULL,
        blank=True, null=True
    )

    fta = models.ForeignKey(FTA, models.PROTECT, verbose_name="FTA")
    importing_country = CountryField()
    issuer = models.ForeignKey(
        Party, models.CASCADE,
        blank=True, null=True,
        related_name="documents_issued"
    )
    exporter = models.ForeignKey(
        Party, models.CASCADE,
        blank=True, null=True,
        related_name="documents_exported"
    )
    importer_name = models.CharField(
        max_length=256, help_text="If known", blank=True, default=""
    )

    document_number = models.CharField(max_length=256, blank=True, default="")
    consignment_ref = models.CharField(max_length=256, blank=True, default="")
    invoice_number = models.CharField(
        "Invoice Number",
        max_length=256, blank=True, default=""
    )
    origin_criteria = models.CharField(
        "Origin Criteria",
        max_length=32, blank=True, default="",
        choices=(
            ("WO", "WO"),
            ("WP", "WP"),
            ("PSR", "PSR"),
            ("other", "Other"),
        )
    )

    # acquitted_at = models.DateTimeField(blank=True, null=True)
    # acquitted_details = JSONField(
    #     default=list, blank=True,
    #     help_text="Acquittal events received"
    # )

    intergov_details = JSONField(
        default=dict, blank=True,
        help_text="Details about communication with the Intergov"
    )
    # https://edi3.org/specs/edi3-regulatory/develop/certificates/#state-lifecycle
    status = models.CharField(
        max_length=12, choices=STATUS_CHOICES, default=STATUS_DRAFT
    )

    class Meta:
        ordering = ('-created_at',)

    def get_absolute_url(self):
        return reverse('documents:detail', args=[self.pk])

    def __str__(self):
        return f"{self.get_type_display()} #{self.short_id}"

    @statsd_timer("model.Document.save")
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

    @property
    def short_id(self):
        return str(self.id)[-6:]

    @property
    def can_be_updated(self):
        return self.status in [
            self.STATUS_DRAFT,
            self.STATUS_SUBMITTED,
            self.STATUS_NOT_ISSUED,
        ]

    def get_igid_text(self):
        if self.status == self.STATUS_DRAFT:
            return None
        if not self.intergov_details.get('object_hash'):
            return None
        return f"https://testnet.trustbridge.io/v/{self.intergov_details.get('object_hash')}"

    def get_igid_image(self):
        text = self.get_igid_text()
        if not text:
            return None
        return get_qrcode_image(text)

    def get_igid_image_base64(self):
        text = self.get_igid_text()
        if not text:
            return None
        return b64encode(self.get_igid_image()).decode("utf-8")


def generate_docfile_filename(instance, filename):
    """
    We completely ignore the original filename for security reasons,
    but we generate our own filename respecting only the original extension if
    provided.
    """
    upload_ref = (
        (str(instance.pk) if instance.pk else None)
        or "ref" + str(uuid.uuid4())
    )
    upload_id = ''.join(
        random.choice(string.ascii_lowercase) for i in range(7)
    )
    if filename and '.' in filename:
        ext = filename.split('.')[-1]
    else:
        # no filename provided - what do we assume?
        ext = 'pdf'

    return 'docfiles/{}/{}.{}'.format(
        upload_ref, upload_id, ext.lower()
    )


class DocumentFile(models.Model):
    id = models.UUIDField(default=uuid.uuid4, primary_key=True)
    doc = models.ForeignKey(
        Document, models.CASCADE,
        related_name="files"
    )
    created_at = models.DateTimeField(default=timezone.now)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, models.CASCADE)

    file = models.FileField(upload_to=generate_docfile_filename)
    filename = models.CharField(
        max_length=1000, blank=True, default="unknown.pdf",
        help_text="Original name of the uploaded file",
    )
    size = models.IntegerField(blank=True, default=None, null=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return str(self.filename)

    @property
    def short_filename(self):
        if len(self.filename) > 25:
            if '.' in self.filename:
                return self.filename[:15] + '...' + self.filename[-10:]
            return self.filename[:22] + '...'
        return self.filename

    def extension(self):
        fname = self.filename or ""
        if "." in fname:
            return fname.rsplit(".", maxsplit=1)[1].upper()
        else:
            return "?"

    def mimetype(self):
        return mimetypes.guess_type(self.filename, strict=False)[0]

    def get_size_display(self):
        def sizeof_fmt(num, suffix='B'):
            for unit in ['', 'Ki', 'Mi', 'Gi', 'Ti', 'Pi', 'Ei', 'Zi']:
                if abs(num) < 1024.0:
                    return "%3.1f%s%s" % (num, unit, suffix)
                num /= 1024.0
            return "%.1f%s%s" % (num, 'Yi', suffix)
        return (
            sizeof_fmt(self.size)
            if self.size
            else ""
        )


class NodeMessage(models.Model):
    STATUS_SENT = "sent"
    STATUS_REJECTED = "rejected"
    STATUS_ACCEPTED = "accepted"

    STATUSES = (
        (STATUS_SENT, "Sent"),
        (STATUS_ACCEPTED, "Accepted"),
        (STATUS_REJECTED, "Rejected"),
    )

    status = models.CharField(
        max_length=16,
        default=STATUS_SENT, choices=STATUSES,
    )

    document = models.ForeignKey(
        Document, models.CASCADE,
        blank=True, null=True
    )
    created_at = models.DateTimeField(
        "Created in the system",
        default=timezone.now,
        help_text="For received messages - when received by us",
    )

    sender_ref = models.CharField(
        max_length=200, unique=True
    )
    subject = models.CharField(
        max_length=200, blank=True, default="",
        help_text="Conversation identificator"
    )
    body = JSONField(
        default=dict, blank=True,
        help_text="generic discrete format, exactly like API returns"
    )
    history = JSONField(
        default=list, blank=True,
        help_text="Status changes and other historical events in a simple format"
    )
    is_outbound = models.BooleanField(default=False)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return self.sender_ref or self.pk

    def trigger_processing(self, new_status=None):
        """
        We don't update business status based on the nodes status changes,
        because it needs a business message, not just transport state change
        """
        # c = self.document
        # b = self.body
        # if new_status:
        #     if b["predicate"] == Predicates.CO_CREATED and self.is_outbound:
        #         if new_status == "accepted" and c.status != c.STATUS_ACCEPTED:
        #             c.status = c.STATUS_ACCEPTED
        #             logger.info("Changing document %s status to accepted", c.short_id)
        #             c.save()
        #             return
        #         if new_status == "rejected" and c.status != c.STATUS_REJECTED:
        #             c.status = c.STATUS_REJECTED
        #             logger.info("Changing document %s status to rejected", c.short_id)
        #             c.save()
        #             return
        #     # TODO: the same for Acquitted and received
        return
