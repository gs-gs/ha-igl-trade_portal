import pytest
from requests.auth import HTTPBasicAuth
from rest_framework.test import APIRequestFactory, force_authenticate, RequestsClient

from trade_portal.documents.models import Document, FTA
from trade_portal.document_api.views import CertificateViewSet
from trade_portal.users.tests.factories import UserFactory

pytestmark = pytest.mark.django_db(transaction=True)


CERT_EXAMPLE = {"certificateOfOrigin": {
  "id": "wfa.org.au:coo:WBC208897",
  "issueDateTime": "2020-06-03T00:46:34Z",
  "name": "CHAFTA Certificate of Origin",
  "attachedFile": {
    "uRI": "https://wfa.org.au/filestore/",
    "encodingCode": "base64",
    "mIMECode": "application/pdf",
    "size": "12600"
  },
  "firstSignatoryAuthentication": {
    "signature": "eyJiNjQiOmZhbHNlLCJjcml0IjpbImI2NCJdLCJhbGciOiJIUzI1NiJ9..5rPBT_XW-x7mjc1ubf4WwW1iV2YJyc4CCFxORIEaAEk",
    "actualDateTime": "2020-05-29T09:46:34Z",
    "statement": "The undersigned hereby declares that the above-stated information is correct and that the goods exported to [importer] comply with the origin requirements specified in the China-Australia Free Trade Agreement."
  },
  "secondSignatoryAuthentication": {
    "signature": "eyJ0eXAiOiJKV1QiLA0KICJhbGciOiJIUzI1NiJ9.eyJpc3MiOiJqb2UiLA0KICJleHAiOjEzMDA4MTkzODAsDQogImh0dHA6Ly9leGFtcGxlLmNvbS9pc19yb290Ijp0cnVlfQ.dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk",
    "actualDateTime": "2020-06-03T03:50:45Z",
    "statement": "On the basis of the control carried out, it is hereby certified that the information herein is correct and that the described goods comply with the origin requirements of the China-Australia Free Trade Agreement."
  },
  "issueLocation": {
    "id": "unece.un.org:locode:AUADL",
    "name": "Adelaide"
  },
  "issuer": {
    "id": "id:wfa.org.au",
    "name": "Australian Grape and Wine Incorporated",
    "postalAddress": {
      "line1": "Level 1, Industry Offcies",
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
    "exportCountry": {
      "code": "AU"
    },
    "exporter": {
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
    "importCountry": {
      "code": "CN"
    },
    "importer": {
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
              "formattedIssueDateTime": "2020-06-02T14:30:00Z",
              "attachedBinaryFile": {
                "uRI": "https://docs.tweglobal.com/8c624a35-9497-41fb-a548-cb5cf43bac21.pdf"
              }
            },
            "tradeProduct": {
              "id": "gs1.org:gtin:9325814006194",
              "description": "Bin 23 Pinot Noir 2018",
              "harmonisedTariffCode": {
                "classCode": "2204.21",
                "className": "Wine of fresh grapes, including fortified wines"
              },
              "originCountry": {
                "code": "AU"
              }
            }
          },
          {
            "sequenceNumber": 2,
            "invoiceReference": {
              "id": "tweglobal.com:invoice:1122345",
              "formattedIssueDateTime": "2020-06-02T14:30:00Z",
              "attachedBinaryFile": {
                "uRI": "https://docs.tweglobal.com/8c624a35-9497-41fb-a548-cb5cf43bac21.pdf"
              }
            },
            "tradeProduct": {
              "id": "gs1.org:gtin:9325814007320",
              "description": "Kalimna Bin 28 Shiraz 2017",
              "harmonisedTariffCode": {
                "classCode": "2204.21",
                "className": "Wine of fresh grapes, including fortified wines"
              },
              "originCountry": {
                "code": "AU"
              }
            }
          }
        ]
      },
      {
        "id": "lindemans.com:shipment:228764",
        "information": "2 pallets (80 cases) Limestone Ridge Shiraz red wine",
        "crossBorderRegulatoryProcedure": {
          "originCriteriaText": "PSR"
        },
        "manufacturer": {
          "id": "id:lindemans.com",
          "name": "Lindemans wine",
          "postalAddress": {
            "line1": "44 Johns way",
            "cityName": "Red Cliffs",
            "postcode": "3496",
            "countrySubDivisionName": "VIC",
            "countryCode": "AU"
          }
        },
        "tradeLineItems": [
          {
            "sequenceNumber": 3,
            "invoiceReference": {
              "id": "tweglobal.com:invoice:8877654",
              "formattedIssueDateTime": "2020-06-05T11:30:00Z",
              "attachedBinaryFile": {
                "uRI": "https://docs.tweglobal.com/03e3754c-906d-4f6d-a592-67447c9119e9.pdf"
              }
            },
            "tradeProduct": {
              "id": "gs1.org:gtin:4088700053621",
              "description": "Coonawarra Trio Limestone Ridge Shiraz Cabernet 2013",
              "harmonisedTariffCode": {
                "classCode": "2204.21",
                "className": "Wine of fresh grapes, including fortified wines"
              },
              "originCountry": {
                "code": "AU"
              }
            }
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
      "usedTransportMeans": {
        "id": "id:B-2398",
        "name": "airbus A350"
      },
      "departureEvent": {
        "departureDateTime": "2020-06-20T09:30:00Z"
      }
    },
    "transportPackages": [
      {
        "id": "gs1.org:sscc:59312345670002345",
        "grossVolume": "0.55 m3",
        "grossWeight": "450 Kg"
      },
      {
        "id": "gs1.org:sscc:59312345670002346",
        "grossVolume": "0.55 m3",
        "grossWeight": "450 Kg"
      },
      {
        "id": "gs1.org:sscc:59312345670002347",
        "grossVolume": "0.55 m3",
        "grossWeight": "450 Kg"
      },
      {
        "id": "gs1.org:sscc:59312345670002348",
        "grossVolume": "0.55 m3",
        "grossWeight": "450 Kg"
      },
      {
        "id": "gs1.org:sscc:59312345670002673",
        "grossVolume": "0.58 m3",
        "grossWeight": "465 Kg"
      },
      {
        "id": "gs1.org:sscc:59312345670002674",
        "grossVolume": "0.58 m3",
        "grossWeight": "465 Kg"
      }
    ],
    "unloadingBaseportLocation": {
      "id": "unece.un.org:locode:CNPVG",
      "name": "Shanghai Pudon International Apt"
    }
  }
}}


def test_integration_workflow():
    # prepare the initial data
    FTA.objects.get_or_create(
        name="China-Australia Free Trade Agreement"
    )
    FTA.objects.get_or_create(
        name="AANZFTA First Protocol"
    )

    u1 = UserFactory()

    # request-related things
    factory = APIRequestFactory()
    c = RequestsClient()
    c.auth = HTTPBasicAuth(u1.username, 'password')

    assert Document.objects.count() == 0
    certificate_body = CERT_EXAMPLE.copy()

    # create some certificate

    resp = c.post(
        'http://testserver/api/documents/v0/certificate/',
        json=certificate_body
    )
    assert resp.status_code == 201, resp.content
    assert 'id' in resp.json()
    cert_id = resp.json().get('id')

    cert = Document.objects.get(pk=cert_id)
    assert Document.objects.count() == 1
    assert cert.document_number == certificate_body["certificateOfOrigin"]["id"]

    # retrieve it
    # resp = c.get(
    #     f'http://testserver/api/documents/v0/certificate/{cert.pk}/',
    # )
    request = factory.get(
        f'api/documents/v0/certificate/{cert.pk}/',
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
        f'api/documents/v0/certificate/{cert.pk}/',
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
