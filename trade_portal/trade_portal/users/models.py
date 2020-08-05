import logging

from django.core.validators import FileExtensionValidator
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.utils.functional import cached_property

logger = logging.getLogger(__name__)


class User(AbstractUser):
    initial_business_id = models.CharField(
        max_length=500,
        help_text="The value provided by user on registration step",
        blank=True, default=""
    )
    mobile_number = models.CharField(
        max_length=32, blank=True, default=""
    )
    verified_mobile_number = models.CharField(
        max_length=32, blank=True, default="",
        help_text="Value appears here only after validation"
    )

    class Meta(AbstractUser.Meta):
        ordering = ("date_joined",)

    def __str__(self):
        fullname = f"{self.first_name} {self.last_name}".strip()
        return fullname or self.email or self.username or super().__str__()

    @cached_property
    def orgs(self):
        # fixme: could be duplicates
        if self.is_staff:
            return Organisation.objects.all()
        else:
            return self.direct_orgs

    @cached_property
    def direct_orgs(self):
        return [om.org for om in self.orgmembership_set.all()]

    def get_current_org(self, session):
        """
        For both staff and normal user
        Returns current (selected manually) or just the first available org
        Because default org is used to create objects for it
        """
        org = None
        current_org_id = session.get("current_org_id") or None
        try:
            if self.is_staff:
                if current_org_id:
                    org = Organisation.objects.get(pk=current_org_id)
                else:
                    org = Organisation.objects.first()
            else:
                current_org_ms = None
                if current_org_id:
                    current_org_ms = OrgMembership.objects.filter(
                        user=self,
                        org_id=current_org_id
                    ).first()
                if not current_org_ms:
                    current_org_ms = OrgMembership.objects.filter(
                        user=self,
                    ).first()
                if current_org_ms:
                    org = current_org_ms.org
        except Exception as e:
            logger.exception(e)
            org = None
        return org

    def get_orgs_with_provided_bid(self):
        return Organisation.objects.filter(
            business_id=self.initial_business_id
        )


class OrgMembership(models.Model):
    ROLE_ADMIN = 'a'
    ROLE_USER = 'u'

    ROLES = (
        (ROLE_ADMIN, 'Admin (can add users)'),
        (ROLE_USER, 'User (can use org but not add users)')
    )

    org = models.ForeignKey("Organisation", models.CASCADE)
    user = models.ForeignKey("User", models.CASCADE)
    since = models.DateTimeField(auto_now_add=True)
    role = models.CharField(max_length=1, choices=ROLES, default=ROLE_USER)

    def __str__(self):
        return f"{self.user} in {self.org}"


class Organisation(models.Model):
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    users = models.ManyToManyField(
        "User", related_name="users",
        through=OrgMembership,
        through_fields=('org', 'user'),
    )
    business_id = models.CharField(
        max_length=64,
        help_text='ABN for Australia',
        blank=True
    )
    dot_separated_id = models.CharField(
        max_length=256, blank=True, default="fill.that.value.au"
    )

    is_trader = models.BooleanField(default=False)
    is_chambers = models.BooleanField(default=False)
    is_regulator = models.BooleanField(default=False)

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name

    def get_type_display(self):
        roles = []
        if self.is_trader:
            roles.append("Trader")
        if self.is_chambers:
            roles.append("Chambers")
        if self.is_regulator:
            roles.append("Regulator")
        return ', '.join(roles)


class OrgRoleRequest(models.Model):
    ROLE_TRADER = "trader"
    ROLE_CHAMBERS = "chambers"

    ROLE_CHOICES = (
        (ROLE_TRADER, "Trader"),
        (ROLE_CHAMBERS, "Chambers"),
    )

    STATUS_REQUESTED = 'requested'
    STATUS_EVIDENCE = 'evidence'
    STATUS_APPROVED = 'approved'
    STATUS_REJECTED = 'rejected'

    STATUS_CHOICES = (
        (STATUS_REQUESTED, "Requested"),
        (STATUS_EVIDENCE, "Evidence"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
    )

    org = models.ForeignKey(Organisation, models.CASCADE)
    created_by = models.ForeignKey(
        User, models.CASCADE, related_name="orgrequests_created"
    )
    created_at = models.DateTimeField(default=timezone.now)
    role = models.CharField(max_length=16, choices=ROLE_CHOICES)

    status = models.CharField(
        max_length=16, default=STATUS_REQUESTED, choices=STATUS_CHOICES
    )
    evidence = models.FileField(
        blank=True, null=True,
        validators=[FileExtensionValidator(allowed_extensions=[
            'jpeg',
            'jpg',
            'png',
            'pdf',
            'doc',
            'docx',
            'odt',
            'gif',
        ])]
    )

    handled_by = models.ForeignKey(
        User, models.SET_NULL, blank=True, null=True,
        related_name="orgrequests_handled"
    )

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return "{} for {}".format(self.get_role_display(), self.org)
