from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):

    def __str__(self):
        fullname = f"{self.first_name} {self.last_name}".strip()
        return fullname or self.email or self.username or super().__str__()

    @property
    def orgs(self):
        # fixme: could be duplicates
        if self.is_staff:
            return Organisation.objects.all()
        else:
            return [om.org for om in self.orgmembership_set.all()]

    def get_current_org(self, session):
        """
        For both staff and normal user
        Returns current (selected manually) or just the first available org
        Because default org is used to create objects for it
        """
        org = None
        current_org_id = session.get("current_org_id") or None

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
        return org


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
    # This model is made for access permissions needs
    TYPE_EXPORTER = 'e'
    TYPE_CHAMBERS = 'c'

    TYPES = (
        # exporters can see all object created for parties with their business ID
        (TYPE_EXPORTER, 'Exporter'),
        # Chambers can see their own created objects
        # and can create documents on behalf of exporters
        (TYPE_CHAMBERS, 'Chambers'),
    )

    name = models.CharField(max_length=255)
    type = models.CharField(max_length=1, choices=TYPES)
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

    class Meta:
        ordering = ("name",)

    def __str__(self):
        return self.name
