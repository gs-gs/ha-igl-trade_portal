import base64
import json
import logging
import urllib

import requests

from django.contrib import messages
from django.views.generic import TemplateView

from trade_portal.documents.models import OaDetails, Document
from trade_portal.documents.services.lodge import AESCipher
from trade_portal.oa_verify.services import (
    OaVerificationService,
    OaVerificationError,
    PdfVerificationService,
)
from trade_portal.monitoring.models import VerificationAttempt

logger = logging.getLogger(__name__)


class OaVerificationView(TemplateView):
    template_name = "oa_verify/verification.html"

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
            the_file = self.request.FILES.get("file-to-verify")
            if not the_file:
                messages.warning(self.request, "The file is not provided")
                return None

            if the_file.name.lower().endswith(".pdf"):
                # PDF workflow
                verify_result = self._verify_pdf_file(the_file)
            else:
                # OA workflow - any other extension is considered to be OA (like .json or .tt)
                value = the_file.read()
                verify_result = self._unpack_and_verify_cleartext(value)

            # logging part
            att = VerificationAttempt.create_from_request(self.request, VerificationAttempt.TYPE_FILE)
            if verify_result.get("doc_number"):
                doc = Document.objects.filter(
                    document_number=verify_result.get("doc_number")
                ).first()
                if doc:
                    att.document = doc
                    att.save()
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

    def _verify_pdf_file(self, the_file):
        """
        Accepting UploadedFile as input (can be read)
        It tries to parse that PDF file and retrieve a valid QR code from it
        Verifying that QR code after that
        https://github.com/gs-gs/ha-igl-project/issues/54
        """
        try:
            valid_qrcodes = PdfVerificationService(the_file).get_valid_qrcodes()
        except Exception as e:
            if "file has not been decrypted" in str(e):
                return {
                    "status": "error",
                    "error_message": (
                        "Verification of encrypted PDF files directly is not supported; "
                        "please use QR code reader and your camera."
                    ),
                }
            else:
                logger.exception(e)
                return {
                    "status": "error",
                    "error_message": (
                        "Unable to parse the PDF file"
                    ),
                }
        if not valid_qrcodes:
            return {
                "status": "error",
                "error_message": (
                    "No QR codes were found in the PDF file; "
                    "Please try to use 'Read QR code using camera' directly"
                ),
            }
        elif len(valid_qrcodes) > 1:
            return {
                "status": "error",
                "error_message": (
                    "There are multiple valid QR codes in that document; "
                    "please scan the desired one manually"
                ),
            }
        return self._parse_and_verify_qrcode(code=valid_qrcodes[0])

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

        va = VerificationAttempt.create_from_request(
            self.request,
            VerificationAttempt.TYPE_LINK
            if query
            else VerificationAttempt.TYPE_QR
        )
        local_oa_details = OaDetails.objects.filter(
            key=key
        ).first()
        if local_oa_details:
            va.document = Document.objects.filter(
                oa=local_oa_details
            ).first()
            va.save()

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
