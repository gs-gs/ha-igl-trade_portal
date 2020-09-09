import pytest
from django.test import Client

pytestmark = pytest.mark.django_db


def test_verification_view_smoke():
    c = Client()
    resp = c.get("/v/")
    assert resp.status_code == 200
    html = resp.content.decode("utf-8")
    assert "function initQrReader()" in html
    assert "id='id-qrcode-submit-form'" in html
