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


class Un20200831CoORenderer:
    def render(self, doc):
        data = {
            "certificateOfOrigin": {
              "id": doc.document_number,
              "issueDateTime": doc.created_at.isoformat(),
              "name": "Certificate of Origin",
              # "attachedFile": {  - filled later based on real binary file
              #   "file": "...",
              #   "encodingCode": "base64",
              #   "mimeCode": "application/pdf"
              # },
              "firstSignatoryAuthentication": {
                "actualDateTime": doc.created_at.isoformat(),
                "statement": (
                    "The undersigned hereby declares that the above-stated information is correct"
                    " and that the goods exported to the importer comply with the origin requirements"
                    " specified in the trade agreement."
                ),
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
                    "postcode": doc.exporter.postcode,
                    "countrySubDivisionName": doc.exporter.countrySubDivisionName,
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
                    # we hardly can determine the importer name for documents created
                    # from UI, but the API ones won't even call this code
                    # "line1": "string",
                    # "line2": "string",
                    # "cityName": "string",
                    # "postcode": "1111",
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
