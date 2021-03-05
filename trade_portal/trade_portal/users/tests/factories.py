from typing import Any, Sequence

from django.contrib.auth import get_user_model
from factory import DjangoModelFactory, Faker, post_generation


class UserFactory(DjangoModelFactory):

    username = Faker("user_name")
    email = Faker("email")

    @post_generation
    def password(self, create: bool, extracted: Sequence[Any], **kwargs):
        self.set_password("password")

    @post_generation
    def org(self, *args, **kwargs):
        from trade_portal.users.models import Organisation, OrgMembership

        o1, _ = Organisation.objects.get_or_create(
            name="first", is_chambers=True, is_regulator=True, is_trader=True
        )
        ms, _ = OrgMembership.objects.get_or_create(
            user=self,
            org=o1,
        )

    class Meta:
        model = get_user_model()
        django_get_or_create = ["username"]
