import pytest
from django.urls import reverse, resolve

pytestmark = pytest.mark.django_db


def test_update():
    assert reverse("users:update") == "/profile/update/"
    assert resolve("/profile/update/").view_name == "users:update"
