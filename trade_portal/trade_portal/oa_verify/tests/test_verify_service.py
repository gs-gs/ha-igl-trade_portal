import json
import os
from unittest import mock

import pytest

from trade_portal.documents.tests.tests_services_lodge import MockResponse
from trade_portal.oa_verify.services import OaVerificationService

pytestmark = pytest.mark.django_db


TYPICAL_VERIFY_RESP = [
    {
        "type": "DOCUMENT_INTEGRITY",
        "name": "OpenAttestationHash",
        "data": True,
        "status": "VALID"
    },
    {
        "status": "SKIPPED",
        "type": "DOCUMENT_STATUS",
        "name": "OpenAttestationEthereumTokenRegistryStatus",
        "reason": {
            "code": 4,
            "codeString": "SKIPPED",
            "message": "Document issuers doesn't have \"tokenRegistry\" property or TOKEN_REGISTRY method"
        }
    },
    {
        "name": "OpenAttestationEthereumDocumentStoreStatus",
        "type": "DOCUMENT_STATUS",
        "data": {
            "issuedOnAll": True,
            "revokedOnAny": False,
            "details": {
                "issuance": [
                    {
                        "issued": True,
                        "address": "0xd1F122506c02063913939acC4451B7C26aD7FCC9"
                    }
                ],
                "revocation": [
                    {
                        "revoked": False,
                        "address": "0xd1F122506c02063913939acC4451B7C26aD7FCC9"
                    }
                ]
            }
        },
        "status": "VALID"
    },
    {
        "status": "SKIPPED",
        "type": "DOCUMENT_STATUS",
        "name": "OpenAttestationDidSignedDocumentStatus",
        "reason": {
            "code": 0,
            "codeString": "SKIPPED",
            "message": "Document was not signed by DID directly"
        }
    },
    {
        "name": "OpenAttestationDnsTxtIdentityProof",
        "type": "ISSUER_IDENTITY",
        "data": [
            {
                "status": "VALID",
                "location": "wpca-alpha.datatrust.link",
                "value": "0xd1F122506c02063913939acC4451B7C26aD7FCC9"
            }
        ],
        "status": "VALID"
    },
    {
        "status": "SKIPPED",
        "type": "ISSUER_IDENTITY",
        "name": "OpenAttestationDnsDidIdentityProof",
        "reason": {
            "code": 0,
            "codeString": "SKIPPED",
            "message": "Document was not issued using DNS-DID"
        }
    }
]


@mock.patch("trade_portal.oa_verify.services.OaVerificationService.kick_verify_api")
@mock.patch("trade_portal.oa_verify.services.OaVerificationService._api_verify_tt_json_file")
def test_verify_tt_document(api_verify_mock, kick_mock):
    ASSETS_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), "assets")

    tt_document = open(os.path.join(ASSETS_PATH, "simple-oa.json"), "rb").read()
    s = OaVerificationService()

    api_verify_mock.return_value = TYPICAL_VERIFY_RESP[:]

    verify_result = s.verify_json_tt_document(tt_document)

    assert kick_mock.call_count == 1
    assert api_verify_mock.call_count == 1

    assert verify_result.get("attachments") == []
    assert verify_result.get("doc_number") == ""
    assert len(verify_result["oa_base64"]) > len(tt_document)
    assert verify_result["status"] == "valid"
    assert verify_result["template_url"] == "https://tutorial-renderer.openattestation.com/"  # asset
    assert verify_result["verify_result"] == api_verify_mock.return_value


@mock.patch("trade_portal.oa_verify.services.OaVerificationService.kick_verify_api")
@mock.patch("trade_portal.oa_verify.services.OaVerificationService._api_verify_tt_json_file")
@mock.patch("requests.get")
@mock.patch("trade_portal.oa_verify.services.OaVerificationService._retrieve_template_url")
def test_verify_pdf_file(retr_mock, get_mock, api_verify_mock, kick_mock):
    ASSETS_PATH = os.path.join(os.path.dirname(os.path.realpath(__file__)), "assets")

    scanned = open(os.path.join(ASSETS_PATH, "scanned-3.pdf"), "rb")
    s = OaVerificationService()

    api_verify_mock.return_value = TYPICAL_VERIFY_RESP[:]
    get_mock.return_value = MockResponse(
        status_code=200,
        json_resp=json.loads(
            open(os.path.join(
                ASSETS_PATH, "trade-get-resp-1f4abad2-adaf-4704-834c-fe2b26db5a63.json"
            ), "rb").read()
        )
    )
    kick_mock.return_value = True
    retr_mock.return_value = "https://template-url/"

    verify_result = s.verify_pdf_file(scanned)

    assert kick_mock.call_count == 1
    assert api_verify_mock.call_count == 1
    assert get_mock.call_count == 1

    assert len(verify_result["attachments"]) == 1
    assert verify_result.get("doc_number") == "WBC208811"
    assert verify_result["status"] == "valid"
    assert verify_result["template_url"] == "https://template-url/"
    assert verify_result["verify_result"] == api_verify_mock.return_value
