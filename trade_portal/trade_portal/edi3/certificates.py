import base64
import logging

try:
    from django.conf import settings
    BID_NAME = settings.BID_NAME
    BID_PREFIX = settings.BID_PREFIX
except ImportError:
    # for non-Django environments just read this variable from somewhere else
    BID_NAME = "ABN"
    BID_PREFIX = "abr.gov.au:abn"

logger = logging.getLogger(__name__)


class CertificateRenderer:

    def render(self, document_obj):
        cert_dict = self.get_minimal_certificate(document_obj)
        # cert_dict.update(self.get_extended_certificate(document_obj))
        return cert_dict

    def get_minimal_certificate(self, doc):
        if doc.type == doc.TYPE_PREF_COO:
            isPreferential = True
        else:
            isPreferential = False
        cert = {
            "id": f"{doc.issuer.dot_separated_id}:coo:{doc.document_number}",
            "issueDateTime": doc.created_at.isoformat(),
            "name": f"{doc.fta} {doc.get_type_display()}",
            "issuer": {
                "id": f"{doc.issuer.full_business_id}",
                "name": doc.issuer.name
            },
            "status": "issued",
            "isPreferential": isPreferential,
            "freeTradeAgreement": str(doc.fta),
            "supplyChainConsignment": {
                "exportCountry": {
                    "code": str(doc.exporter.country),
                },
                "exporter": {
                    "id": f"{doc.exporter.full_business_id}",
                    "name": doc.exporter.name,
                    # "postalAddress": {
                    #   "line1": "161 Collins Street",
                    #   "cityName": "Melbourne",
                    #   "postcode": "3000",
                    #   "countrySubDivisionName": "VIC",
                    #   "countryCode": "AU"
                    # }
                },
                "importCountry": {
                    "code": doc.importing_country.code
                },
                # note: the importer is filled below

                "includedConsignmentItems": [
                    # https://github.com/edi3/edi3-regulatory/blob/develop/docs/certificates/OA-Sample-full.json#L82
                    {
                        "crossBorderRegulatoryProcedure": {
                            "originCriteriaText": doc.origin_criteria,
                        },
                        "tradeLineItems": [
                            {
                                "sequenceNumber": 1,
                                "invoiceReference": {
                                    "id": f"invoice:{doc.invoice_number or 'unknown'}"
                                },
                                "tradeProduct": {
                                    "harmonisedTariffCode": {
                                        "classCode": "2204.21"  # ?
                                    }
                                }
                            }
                        ]
                    }
                ]
            }
        }
        if doc.importer_name:
            cert["importer"] = {
                # "id": "xxx",
                "name": doc.importer_name,
                # postal address is applicable as well
            }
        return cert


class Un20200831CoORenderer:
    def render(self, doc):
        data = {
            "certificateOfOrigin": {
              "id": doc.document_number,
              "issueDateTime": doc.created_at.isoformat(),
              "name": "Certificate of Origin",
              # "attachedFile": {
              #   "file": "...",
              #   "encodingCode": "base64",
              #   "mimeCode": "application/pdf"
              # },
              "firstSignatoryAuthentication": {
                "actualDateTime": doc.created_at.isoformat(),
                # "statement": "string",
                "providingTradeParty": {
                  "id": doc.issuer.full_business_id if doc.issuer else None,
                  "name": doc.issuer.name if doc.issuer else None,
                  "postalAddress": {
                    # "line1": "string",
                    # "line2": "string",
                    # "cityName": "string",
                    # "postcode": "string",
                    # "countrySubDivisionName": "string",
                    "countryCode": doc.sending_jurisdiction.code
                  }
                }
              },
              "issueLocation": {
                "id": doc.sending_jurisdiction.code,
                "name": doc.sending_jurisdiction.name
              },
              "isPreferential": doc.type == doc.TYPE_PREF_COO,
              "freeTradeAgreement": doc.fta.name if doc.fta else None,
              "supplyChainConsignment": {
                # "id": "string",
                # "information": "string",
                "exportCountry": {
                  "code": doc.sending_jurisdiction.code,
                  "name": doc.sending_jurisdiction.name
                },
                "importCountry": {
                  "code": doc.importing_country.code,
                  "name": doc.importing_country.name
                },
                # "includedConsignmentItems": [
                #   {
                #     "id": "string",
                #     "information": "string",
                #     "crossBorderRegulatoryProcedure": {
                #       "originCriteriaText": "string"
                #     },
                #     "manufacturer": {
                #       "id": "string",
                #       "name": "string",
                #       "postalAddress": {
                #         "line1": "string",
                #         "line2": "string",
                #         "cityName": "string",
                #         "postcode": "string",
                #         "countrySubDivisionName": "string",
                #         "countryCode": "AD"
                #       }
                #     },
                #     "tradeLineItems": [
                #       {
                #         "sequenceNumber": 0,
                #         "invoiceReference": {
                #           "id": "string",
                #           "formattedIssueDateTime": "2020-08-30T15:17:31.862Z"
                #         },
                #         "tradeProduct": {
                #           "id": "string",
                #           "description": "string",
                #           "harmonisedTariffCode": {
                #             "classCode": "string",
                #             "className": "string"
                #           },
                #           "originCountry": {
                #             "code": "AD",
                #             "name": "string"
                #           }
                #         },
                #         "transportPackages": [
                #           {
                #             "id": "string",
                #             "grossVolume": {
                #               "uom": "string",
                #               "value": "string"
                #             },
                #             "grossWeight": {
                #               "uom": "string",
                #               "value": "string"
                #             }
                #           }
                #         ]
                #       }
                #     ]
                #   }
                # ],
                # "loadingBaseportLocation": {
                #   "id": "string",
                #   "name": "string"
                # },
                # "mainCarriageTransportMovement": {
                #   "id": "string",
                #   "information": "string",
                #   "departureEvent": {
                #     "departureDateTime": "2020-08-30T15:17:31.862Z"
                #   },
                #   "usedTransportMeans": {
                #     "id": "string",
                #     "name": "string"
                #   }
                # },
                # "unloadingBaseportLocation": {
                #   "id": "string",
                #   "name": "string"
                # }
              }
            }
          }
        # filling some conditional fields
        if doc.issuer:
            data['certificateOfOrigin']["issuer"] = {
                "id": doc.issuer.full_business_id,
                "name": doc.issuer.name,
                "postalAddress": {
                  # "line1": "string",
                  # "line2": "string",
                  # "cityName": "string",
                  # "postcode": "string",
                  # "countrySubDivisionName": "string",
                  "countryCode": str(doc.issuer.country) if doc.issuer.country else None
                }
            }

        if doc.exporter:
            data['certificateOfOrigin']['supplyChainConsignment']["consignor"] = {
                "id": doc.exporter.full_business_id,
                "name": doc.exporter.name,
                "postalAddress": {
                    # "line1": "string",
                    # "line2": "string",
                    # "cityName": "string",
                    # "postcode": "string",
                    # "countrySubDivisionName": "string",
                    "countryCode": (
                        str(doc.exporter.country) if doc.exporter.country else None
                    )
                }
            }
        if doc.importer_name:
            # receiver
            data['certificateOfOrigin']['supplyChainConsignment']["consignee"] = {
                # "id": "CH48834438",
                "name": doc.importer_name,
                "postalAddress": {
                    # "line1": "string",
                    # "line2": "string",
                    # "cityName": "string",
                    # "postcode": "string",
                    # "countrySubDivisionName": "string",
                    "countryCode": str(doc.importing_country)
                }
            }

        pdf_attach = doc.get_pdf_attachment()
        if pdf_attach:
            try:
                data['certificateOfOrigin']['attachedFile'] = {
                    "file": base64.b64encode(pdf_attach.file.read()).decode("utf-8"),
                    "encodingCode": "base64",
                    "mimeCode": pdf_attach.mimetype(),
                }
            except Exception as e:
                logger.exception(e)
                pass
        return data
