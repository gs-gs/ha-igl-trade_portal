try:
    from django.conf import settings
    BID_NAME = settings.BID_NAME
    BID_PREFIX = settings.BID_PREFIX
except ImportError:
    # for non-Django environments just read this variable from somewhere else
    BID_NAME = "ABN"
    BID_PREFIX = "abr.gov.au:abn"


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
