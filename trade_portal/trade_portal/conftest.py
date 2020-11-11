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
