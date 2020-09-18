import random

import pytest
from requests.auth import HTTPBasicAuth
from rest_framework.test import (
    APIRequestFactory, force_authenticate, RequestsClient, APIClient,
)
from django.utils import timezone

from trade_portal.documents.models import Document, FTA
from trade_portal.document_api.views import CertificateViewSet
from trade_portal.users.models import (
    Organisation, OrgMembership, OrganisationAuthToken,
)
from trade_portal.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db(transaction=True)


CERT_EXAMPLE = {
    "certificateOfOrigin": {
        "id": f"APICERT{random.randint(1000, 100000)}",
        "issueDateTime": timezone.now().isoformat(),
        "name": "Certificate of Origin",
        "firstSignatoryAuthentication": {
            "actualDateTime": timezone.now().isoformat(),
            "statement": "I declare it",
            "providingTradeParty": {
                "id": "abr.gov.au:abn:55004094599",
                "name": "TREASURY WINE ESTATES VINTNERS LIMITED",
                "postalAddress": {
                    "line1": "161 Collins Street",
                    "cityName": "Melbourne",
                    "postcode": "3000",
                    "countrySubDivisionName": "VIC",
                    "countryCode": "AU"
                }
            }
        },
        "issueLocation": {
            "id": "unece.un.org:locode:AUADL",
            "name": "Adelaide"
        },
        "issuer": {
            "id": "id:wfa.org.au",
            "name": "Australian Grape and Wine Incorporated",
            "postalAddress": {
                "line1": "Level 1, Industry Offices",
                "line2": "Botanic Road",
                "cityName": "Adelaide",
                "postcode": "5000",
                "countrySubDivisionName": "SA",
                "countryCode": "AU"
            }
        },
        "status": "issued",
        "isPreferential": True,
        "freeTradeAgreement": "China-Australia Free Trade Agreement",
        "supplyChainConsignment": {
            "id": "dbschenker.com:hawb:DBS626578",
            "information": "6 pallets of fine wine, please store below 20 DegC",
            "consignor": {
                "id": "abr.gov.au:abn:55004094599",
                "name": "TREASURY WINE ESTATES VINTNERS LIMITED",
                "postalAddress": {
                    "line1": "161 Collins Street",
                    "cityName": "Melbourne",
                    "postcode": "3000",
                    "countrySubDivisionName": "VIC",
                    "countryCode": "AU"
                }
            },
            "consignee": {
                "id": "id:emw-wines.com",
                "name": "East meets west fine wines",
                "postalAddress": {
                    "line1": "Room 202, Man Po International Business Center",
                    "line2": "No. 664 Xin Hua Rd, Changning District",
                    "cityName": "Shanghai",
                    "postcode": "200052",
                    "countryCode": "CN"
                }
            },
            "exportCountry": {
                "code": "AU",
                "name": "Australia"
            },
            "importCountry": {
                "code": "SG",
                "name": "Singapore"
            },
            "includedConsignmentItems": [
                {
                    "id": "penfolds.com:shipment:4738291",
                    "information": "2 pallets (80 cases) Bin23 Pinot and 2 pallets (80 cases) Bin 28 Shiraz",
                    "crossBorderRegulatoryProcedure": {
                        "originCriteriaText": "WP"
                    },
                    "manufacturer": {
                        "id": "id:penfolds.com",
                        "name": "Penfolds wine",
                        "postalAddress": {
                            "line1": "Penfolds vineyard",
                            "cityName": "Bordertown",
                            "postcode": "5268",
                            "countrySubDivisionName": "SA",
                            "countryCode": "AU"
                        }
                    },
                    "tradeLineItems": [
                        {
                            "sequenceNumber": 1,
                            "invoiceReference": {
                                "id": "tweglobal.com:invoice:1122345",
                                "formattedIssueDateTime": "2020-08-30T15:17:31.862Z"
                            },
                            "tradeProduct": {
                                "id": "gs1.org:gtin:9325814006194",
                                "description": "Bin 23 Pinot Noir 2018",
                                "harmonisedTariffCode": {
                                    "classCode": "2204.21",
                                    "className": "Wine of fresh grapes, including fortified wines"
                                },
                                "originCountry": {
                                    "code": "AU",
                                    "name": "Australia"
                                }
                            },
                            "transportPackages": [
                                {
                                    "id": "gs1.org:sscc:59312345670002345",
                                    "grossVolume": {
                                        "uom": "m3",
                                        "value": "0.55"
                                    },
                                    "grossWeight": {
                                        "uom": "Kg",
                                        "value": "450"
                                    }
                                }
                            ]
                        }
                    ]
                }
            ],
            "loadingBaseportLocation": {
                "id": "unece.un.org:locode:AUMEL",
                "name": "Melbourne"
            },
            "mainCarriageTransportMovement": {
                "id": "iata.org:CX104",
                "information": "Cathay Pacific Flight CX 104 Melbourne to Shangai",
                "departureEvent": {
                    "departureDateTime": "2020-08-30T15:17:31.862Z"
                },
                "usedTransportMeans": {
                    "id": "id:B-2398",
                    "name": "Airbus A350"
                }
            },
            "unloadingBaseportLocation": {
                "id": "unece.un.org:locode:CNPVG",
                "name": "Shanghai Pudon International Apt"
            }
        }
    }
}


@pytest.fixture
def docapi_env():
    ret = {}
    FTA.objects.get_or_create(
        name="China-Australia Free Trade Agreement"
    )
    FTA.objects.get_or_create(
        name="AANZFTA First Protocol"
    )
    ret["u1"] = UserFactory()
    ret["u2"] = UserFactory()

    # hacky move u2 to org2
    org2 = Organisation.objects.create(
        name="Regulator",
        is_regulator=True
    )
    ms = OrgMembership.objects.get(
        user=ret["u2"],
    )
    ms.org = org2
    ms.save()

    # create 2 tokens
    ret["t1"] = OrganisationAuthToken.objects.create(
        user=ret["u1"],
        org=ret["u1"].direct_orgs[0]
    )
    ret["t2"] = OrganisationAuthToken.objects.create(
        user=ret["u2"],
        org=ret["u2"].direct_orgs[0]
    )

    return ret


def test_integration_workflow(docapi_env):
    u1 = UserFactory()

    # request-related things
    factory = APIRequestFactory()
    c = RequestsClient()
    c.auth = HTTPBasicAuth(u1.username, 'password')

    assert Document.objects.count() == 0
    certificate_body = CERT_EXAMPLE.copy()

    # create some certificate

    resp = c.post(
        'http://testserver/api/documents/v0/CertificatesOfOrigin/',
        json=certificate_body
    )
    assert resp.status_code == 201, resp.content
    assert 'id' in resp.json()
    cert_id = resp.json().get('id')

    cert = Document.objects.get(pk=cert_id)
    assert Document.objects.count() == 1
    assert cert.document_number == certificate_body[
        "certificateOfOrigin"]["id"]

    # retrieve it
    request = factory.get(
        f'api/documents/v0/CertificatesOfOrigin/{cert.pk}/',
        {
            "certificateOfOrigin": {
                "freeTradeAgreement": "CHAFTA",
                "name": "lalala"
            }
        },
        format='json'
    )
    force_authenticate(request, user=u1)
    resp = CertificateViewSet.as_view({"get": "retrieve"})(request, pk=cert.pk)
    assert resp.status_code == 200, resp.data
    cert_data = resp.data["certificateOfOrigin"]
    assert resp.data["id"] == cert.pk
    assert cert_data[
        "freeTradeAgreement"] == "China-Australia Free Trade Agreement"
    cert.refresh_from_db()
    assert cert.fta and cert.fta.name == "China-Australia Free Trade Agreement"

    # update it
    request = factory.patch(
        f'api/documents/v0/CertificatesOfOrigin/{cert.pk}/',
        {
            "certificateOfOrigin": {
                "freeTradeAgreement": "AANZFTA First Protocol",
                "name": "lalala"
            }
        },
        format='json'
    )
    force_authenticate(request, user=u1)
    resp = CertificateViewSet.as_view({"patch": "update"})(request, pk=cert.pk)
    assert resp.status_code == 200, resp.data
    cert.refresh_from_db()
    cert_data = cert.raw_certificate_data["certificateOfOrigin"]
    # just ensure that we didn't overwrite all the data
    assert len(cert_data.keys()) > 5, cert_data
    assert cert_data["freeTradeAgreement"] == "AANZFTA First Protocol"
    assert cert.fta and cert.fta.name == "AANZFTA First Protocol"

    # TODO: file upload
    # TODO: change status
    return


def test_org_permission_to_create(docapi_env):
    t1 = docapi_env["t1"]
    t2 = docapi_env["t2"]

    # now - the test
    c = APIClient()

    # create some certificate - fail - because u2/org2 is regulator
    c.credentials(HTTP_AUTHORIZATION=f'Token {t2.access_token}')
    resp = c.post(
        '/api/documents/v0/CertificatesOfOrigin/',
        CERT_EXAMPLE,
        format='json'
    )
    assert resp.status_code == 405, resp.content

    # u1/o1 is fine
    c.credentials(HTTP_AUTHORIZATION=f'Token {t1.access_token}')
    resp = c.post(
        '/api/documents/v0/CertificatesOfOrigin/',
        CERT_EXAMPLE,
        format='json'
    )
    assert resp.status_code == 201, resp.content


def test_very_wrong_payloads(docapi_env):
    c = APIClient()
    # create some certificate - fail - because u2/org2 is regulator
    c.credentials(HTTP_AUTHORIZATION=f'Token {docapi_env["t1"].access_token}')

    # empty payload
    resp = c.post(
        '/api/documents/v0/CertificatesOfOrigin/',
    )
    assert resp.status_code == 400, resp.content
    assert resp.json() == {'payload': 'certificateOfOrigin must be provided'}

    # wrong schema
    resp = c.post(
        '/api/documents/v0/CertificatesOfOrigin/',
        {
            "certificateOfOrigin": {
                "not": "Expected",
            }
        },
        format="json"
    )
    assert resp.status_code == 400, resp.content
    assert resp.json() == {'exportCountry': 'must be a dict with code key'}
