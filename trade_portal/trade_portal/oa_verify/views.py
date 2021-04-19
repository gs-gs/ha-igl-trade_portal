import json
import logging

from constance import config
from django.contrib import messages
from django.views.generic import TemplateView

from trade_portal.documents.models import OaDetails, Document
from trade_portal.oa_verify.services import OaVerificationService
from trade_portal.monitoring.models import VerificationAttempt

logger = logging.getLogger(__name__)


class OaVerificationView(TemplateView):
    """
    Base OA verification view, rendering template and acceping POST Form request
    Then just calls corresponding service; avoid having any real verification code here
    otherwise it gets duplicated between API and UI endpoints.
    """
    template_name = "oa_verify/verification.html"

    def get_context_data(self, *args, **kwargs):
        c = super().get_context_data(*args, **kwargs)
        c["VERIFIER_SHOW_DOWNLOAD_TAB"] = config.VERIFIER_SHOW_DOWNLOAD_TAB

        if self.request.POST:
            try:
                c["verification_result"] = self.perform_verification()
            except Exception as e:
                logger.exception(e)
                pass
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
                        "Verification attempt for type '{}' != 'document".format(
                            q['type']
                        )
                    )
                uri = q["payload"]["uri"]
                key = q["payload"]["key"]
            except Exception as e:
                logger.exception(e)
                messages.warning(
                    self.request,
                    "This verification request can't be parsed due to lack of "
                    "parameters or format being invalid",
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
                messages.warning(self.request, "No file provided, please upload one")
                return None

            if the_file.name.lower().endswith(".pdf"):
                # PDF workflow
                verify_result = OaVerificationService().verify_pdf_file(the_file)
            else:
                # OA workflow - any other extension is considered to be OA (like .json or .tt)
                tt_content = the_file.read()
                verify_result = OaVerificationService().verify_json_tt_document(tt_content)

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
                verify_result = OaVerificationService().verify_qr_code(query=query)
                va = VerificationAttempt.create_from_request(
                    self.request,
                    VerificationAttempt.TYPE_LINK
                )
                local_oa_details = OaDetails.objects.filter(
                    key=query["key"]
                ).first()
                if local_oa_details:
                    va.document = Document.objects.filter(
                        oa=local_oa_details
                    ).first()
                    va.save()
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
                verify_result = OaVerificationService().verify_qr_code(code=the_code)
                # TODO: create that log object if we still need it
                va = VerificationAttempt.create_from_request(
                    self.request,
                    VerificationAttempt.TYPE_QR
                )
                doc = Document.objects.filter(
                    document_number=verify_result.get("doc_number")
                ).first()
                if doc:
                    att.document = doc
                    att.save()
            except Exception as e:
                logger.exception(e)
                verify_result = {
                    "status": "error",
                    "error_message": "The QR code seems to be invalid or unsupported",
                }
        else:
            return None
        return verify_result
