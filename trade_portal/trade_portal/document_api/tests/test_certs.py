import pytest
from requests.auth import HTTPBasicAuth
from rest_framework.test import (
  APIRequestFactory, force_authenticate, RequestsClient, APIClient,
)

from trade_portal.documents.models import Document, FTA
from trade_portal.document_api.views import CertificateViewSet
from trade_portal.users.models import (
  Organisation, OrgMembership, OrganisationAuthToken,
)
from trade_portal.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db(transaction=True)


CERT_EXAMPLE = {
    "certificateOfOrigin": {
      "id": "wcaaba9320",
      "issueDateTime": "2020-08-30T15:17:31.862Z",
      "name": "Certificate of Origin",
      "attachedFile": {
        "file": "base64lalala",
        "encodingCode": "base64",
        "mimeCode": "application/pdf"
      },
      "firstSignatoryAuthentication": {
        "actualDateTime": "2020-08-30T15:17:31.862Z",
        "statement": "string",
        "providingTradeParty": {
          "id": "string",
          "name": "string",
          "postalAddress": {
            "line1": "string",
            "line2": "string",
            "cityName": "string",
            "postcode": "string",
            "countrySubDivisionName": "string",
            "countryCode": "AD"
          }
        }
      },
      "issueLocation": {
        "id": "string",
        "name": "string"
      },
      "issuer": {
        "id": "12345678901",
        "name": "CompanyName",
        "postalAddress": {
          "line1": "string",
          "line2": "string",
          "cityName": "string",
          "postcode": "string",
          "countrySubDivisionName": "string",
          "countryCode": "AD"
        }
      },
      "isPreferential": True,
      "freeTradeAgreement": "China-Australia Free Trade Agreement",
      "supplyChainConsignment": {
        "id": "string",
        "information": "string",
        "consignee": {
          "id": "CH48834438",
          "name": "Receiver China Ltd",
          "postalAddress": {
            "line1": "string",
            "line2": "string",
            "cityName": "string",
            "postcode": "string",
            "countrySubDivisionName": "string",
            "countryCode": "AD"
          }
        },
        "consignor": {
          "id": "12345678901",
          "name": "Sender Australia Inc",
          "postalAddress": {
            "line1": "string",
            "line2": "string",
            "cityName": "string",
            "postcode": "string",
            "countrySubDivisionName": "string",
            "countryCode": "AD"
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
            "id": "string",
            "information": "string",
            "crossBorderRegulatoryProcedure": {
              "originCriteriaText": "string"
            },
            "manufacturer": {
              "id": "string",
              "name": "string",
              "postalAddress": {
                "line1": "string",
                "line2": "string",
                "cityName": "string",
                "postcode": "string",
                "countrySubDivisionName": "string",
                "countryCode": "AD"
              }
            },
            "tradeLineItems": [
              {
                "sequenceNumber": 0,
                "invoiceReference": {
                  "id": "string",
                  "formattedIssueDateTime": "2020-08-30T15:17:31.862Z"
                },
                "tradeProduct": {
                  "id": "string",
                  "description": "string",
                  "harmonisedTariffCode": {
                    "classCode": "string",
                    "className": "string"
                  },
                  "originCountry": {
                    "code": "AD",
                    "name": "string"
                  }
                },
                "transportPackages": [
                  {
                    "id": "string",
                    "grossVolume": {
                      "uom": "string",
                      "value": "string"
                    },
                    "grossWeight": {
                      "uom": "string",
                      "value": "string"
                    }
                  }
                ]
              }
            ]
          }
        ],
        "loadingBaseportLocation": {
          "id": "string",
          "name": "string"
        },
        "mainCarriageTransportMovement": {
          "id": "string",
          "information": "string",
          "departureEvent": {
            "departureDateTime": "2020-08-30T15:17:31.862Z"
          },
          "usedTransportMeans": {
            "id": "string",
            "name": "string"
          }
        },
        "unloadingBaseportLocation": {
          "id": "string",
          "name": "string"
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
    assert cert.document_number == certificate_body["certificateOfOrigin"]["id"]

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
    assert cert_data["freeTradeAgreement"] == "China-Australia Free Trade Agreement"
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
