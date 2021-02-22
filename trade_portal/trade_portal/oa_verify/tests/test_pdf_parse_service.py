import os

import pytest

from trade_portal.oa_verify.services import PdfVerificationService


pytestmark = pytest.mark.django_db


def test_pdf_parse_service():
    ASSETS_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), "assets")

    no_qrcode_file = open(os.path.join(ASSETS_PATH, "no-qr-code.pdf"), "rb")
    s = PdfVerificationService(no_qrcode_file)
    assert s.get_valid_qrcodes() is None

    tt_qrcode = open(os.path.join(ASSETS_PATH, "tt_qr_code_format.pdf"), "rb")
    s = PdfVerificationService(tt_qrcode)
    assert s.get_valid_qrcodes() == [(
        """tradetrust://{"uri":"https://trade.c1.devnet.trustbridge.io/oa/b429b963-9701-4395-8e83-7459c2e3010c/"""
        """#EB7DE6F92EA972205420AC23D6279BF4B8ADB5B4E0435E1CAC358293BBDAACB4"}"""
    )]
    http_2_qrcodes = open(os.path.join(ASSETS_PATH, "http_format_2_qr_codes.pdf"), "rb")
    s = PdfVerificationService(http_2_qrcodes)
    assert s.get_valid_qrcodes() == [(
        """https://trade.c1.devnet.trustbridge.io/v/?q=%7B%22type%22%3A%20%22DOCUMENT%22%2C%20%22"""
        """payload%22%3A%20%7B%22uri%22%3A%20%22https%3A//trade.c1.devnet.trustbridge.io/oa/819c9"""
        """52d-2455-4277-aa59-74654d235cc8/%22%2C%20%22key%22%3A%20%22DDBF2CD26963F8538563947560F"""
        """878A36B44E93EBF72C09AC98B6B65BF6FA7EB%22%7D%7D"""
    )]

    single = open(os.path.join(ASSETS_PATH, "cert-AANZFTA.pdf"), "rb")
    s = PdfVerificationService(single)
    assert s.get_valid_qrcodes() == [(
        """https://trade.c1.devnet.trustbridge.io/v/?q=%7B%22type%22%3A%20%22DOCUMENT%22%2C%20%22"""
        """payload%22%3A%20%7B%22uri%22%3A%20%22https%3A//trade.c1.devnet.trustbridge.io/oa/1f4ab"""
        """ad2-adaf-4704-834c-fe2b26db5a63/%22%2C%20%22key%22%3A%20%22BCE7AC1B7BAFA6D2FB18775F63D"""
        """770A293757D19E5A58A013478F4A73712A09B%22%7D%7D"""
    )]

    # Scanned PDFs both using PDF Form and Image objects
    scanned = open(os.path.join(ASSETS_PATH, "cert-AANZFTA-rasterised.pdf"), "rb")
    s = PdfVerificationService(scanned)
    assert s.get_valid_qrcodes() == [
        """https://trade.c1.devnet.trustbridge.io/v/?q=%7B%22type%22%3A%20%22DOCUMENT%22%2C%20%22"""
        """payload%22%3A%20%7B%22uri%22%3A%20%22https%3A//trade.c1.devnet.trustbridge.io/oa/1f4ab"""
        """ad2-adaf-4704-834c-fe2b26db5a63/%22%2C%20%22key%22%3A%20%22BCE7AC1B7BAFA6D2FB18775F63D"""
        """770A293757D19E5A58A013478F4A73712A09B%22%7D%7D"""
    ]

    scanned = open(os.path.join(ASSETS_PATH, "cert-AANZFTA-rasterised-3-equal-qrcodes.pdf"), "rb")
    s = PdfVerificationService(scanned)
    assert s.get_valid_qrcodes() == [
        """https://trade.c1.devnet.trustbridge.io/v/?q=%7B%22type%22%3A%20%22DOCUMENT%22%2C%20%22"""
        """payload%22%3A%20%7B%22uri%22%3A%20%22https%3A//trade.c1.devnet.trustbridge.io/oa/1f4ab"""
        """ad2-adaf-4704-834c-fe2b26db5a63/%22%2C%20%22key%22%3A%20%22BCE7AC1B7BAFA6D2FB18775F63D"""
        """770A293757D19E5A58A013478F4A73712A09B%22%7D%7D"""
    ]

    scanned = open(os.path.join(ASSETS_PATH, "scanned-3.pdf"), "rb")
    s = PdfVerificationService(scanned)
    assert s.get_valid_qrcodes() == [
        """https://trade.c1.devnet.trustbridge.io/v/?q=%7B%22type%22%3A%20%22DOCUMENT%22%2C%20%22"""
        """payload%22%3A%20%7B%22uri%22%3A%20%22https%3A//trade.c1.devnet.trustbridge.io/oa/1f4ab"""
        """ad2-adaf-4704-834c-fe2b26db5a63/%22%2C%20%22key%22%3A%20%22BCE7AC1B7BAFA6D2FB18775F63D"""
        """770A293757D19E5A58A013478F4A73712A09B%22%7D%7D"""
    ]

    scanned = open(os.path.join(ASSETS_PATH, "2-different-qrcodes-duplicates-rasterized.pdf"), "rb")
    s = PdfVerificationService(scanned)
    assert sorted(s.get_valid_qrcodes()) == sorted([
        """https://trade.c1.devnet.trustbridge.io/v/?q=%7B%22type%22%3A%20%22DOCUMENT%22%2C%20%22"""
        """payload%22%3A%20%7B%22uri%22%3A%20%22https%3A//trade.c1.devnet.trustbridge.io/oa/1f4ab"""
        """ad2-adaf-4704-834c-fe2b26db5a63/%22%2C%20%22key%22%3A%20%22BCE7AC1B7BAFA6D2FB18775F63D"""
        """770A293757D19E5A58A013478F4A73712A09B%22%7D%7D""",
        """https://trade.c1.devnet.trustbridge.io/v/?q=%7B%22type%22%3A%20%22DOCUMENT%22%2C%20%22"""
        """payload%22%3A%20%7B%22uri%22%3A%20%22https%3A//trade.c1.devnet.trustbridge.io/oa/819c9"""
        """52d-2455-4277-aa59-74654d235cc8/%22%2C%20%22key%22%3A%20%22DDBF2CD26963F8538563947560F"""
        """878A36B44E93EBF72C09AC98B6B65BF6FA7EB%22%7D%7D"""
    ])
