import base64
import json
import logging
import urllib

import requests

from django.contrib import messages
from django.views.generic import TemplateView

from trade_portal.documents.services.lodge import AESCipher
from trade_portal.oa_verify.services import (
    OaVerificationService,
    OaVerificationError,
)

logger = logging.getLogger(__name__)


class OaVerificationView(TemplateView):
    template_name = "oa_verify/verification.html"

    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        c = super().get_context_data(*args, **kwargs)

        if self.request.POST:
            c["verification_result"] = self.perform_verification()
        else:
            query_query = self._get_qr_code_query()
            if query_query:
                c["verification_result"] = self.perform_verification(query=query_query)
        return c

    def _get_qr_code_query(self):
        """
        If there was a QR code link with our portal as the first parameter
        and there is 'q' GET parameter - parse it and ensure it's a JSON
        with somere required fields; if so - parse it and verify.
        """
        q = self.request.GET.get("q")
        if q:
            try:
                q = json.loads(q)
                if q["type"] != "DOCUMENT":
                    raise Exception(
                        "Somebody is trying to verify something which is not a document"
                    )
                uri = q["payload"]["uri"]
                key = q["payload"]["key"]
            except Exception as e:
                logger.exception(e)
                messages.warning(
                    self.request,
                    "There is a verification request which can't be parsed",
                )
            else:
                # the JSON is valid and some parameters are present
                return {"uri": uri, "key": key}
        return None

    def post(self, request, *args, **kwargs):
        # get_context_data calls the verification step if the data is present
        return super().get(request, *args, **kwargs)

    def perform_verification(self, query: dict = None):
        """
        Return dict of the next format:
        {
            "status": "valid|invalid|error",

            # only if valid
            "attachments": [list of attachments to that OA doc to display them to user]
            "unwrapped_file": {...},

            # always present
            "verify_result": [list of dicts describing verification aspects]
            "verify_result_rotated": {dict of aspects->messages}

            # present only for errors (not invalid but real errors)
            "error_message":
        }

        Please note that invalid means that file is okay but not issued/tampered/etc
        but error means that the file is not OA file or API returns 500 errors
        """
        if self.request.POST.get("type") == "file":
            the_file = self.request.FILES["oa_file"]
            value = the_file.read()
            verify_result = self._unpack_and_verify_cleartext(value)
        elif query:
            # ?q={...}
            try:
                verify_result = self._parse_and_verify_qrcode(query=query)
            except Exception as e:
                if str(e) == "Nonce cannot be empty":
                    verify_result = {
                        "status": "error",
                        "error_message": (
                            "The query seems to be invalid or unsupported "
                            "(most likely the document is not issued yet)"
                        ),
                    }
                else:
                    logger.exception(e)
                    verify_result = {
                        "status": "error",
                        "error_message": f"The query seems to be invalid or unsupported ({str(e)})",
                    }
        elif self.request.POST.get("type") == "qrcode":
            the_code = self.request.POST.get("qrcode")
            try:
                verify_result = self._parse_and_verify_qrcode(code=the_code)
            except Exception as e:
                logger.exception(e)
                verify_result = {
                    "status": "error",
                    "error_message": "The QR code seems to be invalid or unsupported",
                }
        return verify_result

    def _unpack_and_verify_cleartext(self, cleartext):
        return OaVerificationService().verify_file(cleartext)

    def _parse_and_verify_qrcode(self, code: str = None, query: dict = None):
        """
        2 kinds of QR codes:

        1. new one self-contained
        https://action.openattestation.com/?q={q}
        where q is urlencoded JSON something like
        {
            "type": "DOCUMENT",
            "payload": {
                "uri": "https://trade.c1.devnet.trustbridge.io/oa/1d490b1b-aee8-47f3-bfa5-d08c67e940eb/",
                "key": "DC97D0BA857D6FC213959F6F42E77AF0426C8329ABF3855B5000FED82B86E82C",
                "permittedActions": ["VIEW"],
                "redirect": "https://dev.tradetrust.io"
            }
        }

        2. old one, just tradetrust data
        tradetrust://{"uri":"https://trade.c1.devnet.trustbridge.io/oa/1d490b1b-aee8-47f3-bfa5-d08c67e940eb/#DC97D0BA857D6FC213959F6F42E77AF0426C8329ABF3855B5000FED82B86E82C"}

        Note we catch all exceptions one layer above, so no need to do it here

        """
        if code:
            # has been read by QR reader
            if code.startswith("https://") or code.startswith("http://"):
                # new approach
                components = urllib.parse.urlparse(code)
                params = urllib.parse.parse_qs(components.query)
                req = json.loads(params["q"][0])
                if req["type"].upper() == "DOCUMENT":
                    uri = req["payload"]["uri"]
                    key = req["payload"]["key"]  # it's always AES
            elif code.startswith("tradetrust://"):
                # old approach
                json_body = code.split("://", maxsplit=1)[1]
                params = json.loads(json_body)["uri"]
                uri, key = params.rsplit("#", maxsplit=1)
            else:
                raise OaVerificationError("Unsupported QR code format")
        elif query:
            # the url has been navigated, so we already have both uri and key
            uri, key = query["uri"], query["key"]

        # this will contain fields cipherText, iv, tag, type
        logger.info("Retrieving document %s having key %s", uri, key)

        try:
            document_info = requests.get(uri).json()["document"]
        except Exception as e:
            logger.exception(e)
            raise OaVerificationError(
                "Unable to download the OA document from given url (this usually "
                "means that remote service is down or acting incorrectly"
            )

        cp = AESCipher(key)
        cleartext_b64 = cp.decrypt(
            document_info["iv"],
            document_info["tag"],
            document_info["cipherText"],
        ).decode("utf-8")
        cleartext = base64.b64decode(cleartext_b64)

        logger.info("Unpacking document %s", uri)

        return self._unpack_and_verify_cleartext(cleartext)
