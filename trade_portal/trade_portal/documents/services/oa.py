import datetime

import requests
from django.conf import settings

from trade_portal.documents.models import Document


class OaApiRestClient:
    """
    Client working with our OA wrap API, moved out for easy mocking in tests,
    code separation and possible replacement by native code
    """

    def wrap_document(self, oa_doc):
        if getattr(settings, "IS_UNITTEST", False) is True:
            raise EnvironmentError("This procedure must not be called from unittest")
        return requests.post(
            settings.OA_WRAP_API_URL + "/document/wrap",
            json={
                "document": oa_doc,
                "params": {
                    "version": "https://schema.openattestation.com/2.0/schema.json",
                },
            },
        )


class OaV2Renderer:

    def render_oa_v2_document(self, document: Document, subject: str) -> dict:
        tt_host = settings.OA_NOTARY_DOMAIN or settings.BASE_URL
        tt_key_location = tt_host.replace("https://", "").replace(
            "http://", ""
        )

        if ":" in tt_key_location:
            tt_key_location = tt_key_location.split(":", maxsplit=1)[0]

        rendered_oa = {
            "version": "open-attestation/2.0",
            "reference": subject,
            "name": f"OA document for {document.get_type_display()}",
            "validFrom": datetime.datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "$template": {
                "name": "COO",
                "type": "EMBEDDED_RENDERER",
                "url": settings.OA_RENDERER_HOST,
                # "url": "https://chafta.tradetrust.io"
            },
            # OAv2 field
            "issuers": [
                {
                    "name": document.issuer.name,
                    "documentStore": settings.OA_NOTARY_CONTRACT,
                    "identityProof": {
                        "type": "DNS-TXT",
                        "location": tt_key_location,
                    },
                }
            ],
            "recipient": {
                "name": document.importer_name or "",
            },
        }
        return rendered_oa

    # this is not used but may be in the future versions
    # def _render_uploaded_files(self, document: Document) -> list:
    #     uploaded = []
    #     for file in document.files.all():
    #         file.file
    #         mt, enc = mimetypes.guess_type(file.filename, strict=False)
    #         uploaded.append(
    #             {
    #                 "type": mt or "binary/octet-stream",
    #                 "filename": file.filename,
    #                 "data": base64.b64encode(file.file.read()).decode("utf-8"),
    #             }
    #         )
    #     return uploaded
