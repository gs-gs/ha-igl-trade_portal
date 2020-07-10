try:
    from django.conf import settings
    BID_NAME = settings.BID_NAME
except ImportError:
    BID_NAME = "ABN"


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
        return {
          "id": f"{doc.issuer.dot_separated_id}:coo:{doc.document_number}",
          "issueDateTime": doc.created_at.isoformat(),
          "name": f"{doc.fta} {doc.get_type_display()}",
          "issuer": {
            "id": f"id:{doc.issuer.dot_separated_id}",
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
              "id": (
                f"abr.gov.au:abn:{doc.exporter.business_id}"
              ) if settings.BID_NAME == "ABN" else f"gov.sg:UEN:{doc.exporter.business_id}",
              "name": doc.exporter.name
            },
            "importCountry": {
              "code": doc.importing_country.code
            },
            "includedConsignmentItems": [
              {
                "crossBorderRegulatoryProcedure": {
                  "originCriteriaText": doc.origin_criteria,
                },
                "tradeLineItems": [
                  {
                    "sequenceNumber": 1,
                    "invoiceReference": {
                      "id": f"tweglobal.com:invoice:{doc.invoice_number or None}"
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
