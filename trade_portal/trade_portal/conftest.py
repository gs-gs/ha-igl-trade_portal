import pytest
from django.test import Client, RequestFactory

from trade_portal.users.models import User
from trade_portal.users.tests.factories import UserFactory


@pytest.fixture(autouse=True)
def media_storage(settings, tmpdir):
    settings.MEDIA_ROOT = tmpdir.strpath


@pytest.fixture
def user() -> User:
    return UserFactory()


@pytest.fixture
def request_factory() -> RequestFactory:
    return RequestFactory()


@pytest.fixture
def normal_user(db):
    user = UserFactory(is_staff=False, is_superuser=False, is_active=True)
    user.set_password("password")
    user.save()
    user.web_client = Client()
    user.web_client.login(username=user.username, password="password")
    return user


@pytest.fixture
def staff_user(db):
    user = UserFactory(is_staff=True, is_superuser=False, is_active=True)
    user.set_password("password")
    user.save()
    user.web_client = Client()
    user.web_client.login(username=user.username, password="password")
    return user


@pytest.fixture
def ftas(db):
    from trade_portal.documents.models import FTA
    FTA.objects.get_or_create(name="Test FTA", country=["SG", "AU", "CN", "GB"])


@pytest.fixture
def docapi_env(scope="session"):
    from trade_portal.documents.models import FTA
    from trade_portal.users.models import (
        Organisation,
        OrgMembership,
        OrganisationAuthToken,
    )

    ret = {}
    FTA.objects.get_or_create(name="China-Australia Free Trade Agreement")
    FTA.objects.get_or_create(name="AANZFTA First Protocol")
    ret["u1"] = UserFactory()
    ret["u2"] = UserFactory()

    # hacky move u2 to org2
    org2 = Organisation.objects.create(name="Regulator", is_regulator=True)
    ms = OrgMembership.objects.get(
        user=ret["u2"],
    )
    ms.org = org2
    ms.save()

    # create 2 tokens
    ret["t1"] = OrganisationAuthToken.objects.create(
        user=ret["u1"], org=ret["u1"].direct_orgs[0]
    )
    ret["t2"] = OrganisationAuthToken.objects.create(
        user=ret["u2"], org=ret["u2"].direct_orgs[0]
    )

    return ret
