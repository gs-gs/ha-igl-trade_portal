import base64
import json
import logging
import urllib

import requests

from constance import config
from django.contrib import messages
from django.views.generic import TemplateView

from trade_portal.documents.services.lodge import AESCipher

logger = logging.getLogger(__name__)


class OaVerificationView(TemplateView):
    template_name = "oa_verify/verification.html"

    def dispatch(self, request, *args, **kwargs):
        self.verify_result = None
        self.verdict = None
        self.metadata = None
        self.attachments = []
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        c = super().get_context_data(*args, **kwargs)
        c['verify_result'] = self.verify_result
        c['verdict'] = self.verdict
        c['metadata'] = self.metadata
        c['attachments'] = self.attachments
        return c

    def post(self, request, *args, **kwargs):
        if request.POST.get("type") == "file":
            the_file = request.FILES["oa_file"]
            value = the_file.read()
            self._unpack_and_verify_cleartext(value)
        elif request.POST.get("type") == "qrcode":
            the_code = request.POST.get("qrcode")
            try:
                self._parse_and_verify_qrcode(the_code)
            except Exception as e:
                logger.exception(e)
                messages.error(request, "The code seems to be invalid or unsupported")

        return super().get(request, *args, **kwargs)

    def _unpack_and_verify_cleartext(self, cleartext):
        self.verify_result = self._verify_file(cleartext)
        if isinstance(self.verify_result, list):
            self.verdict = "valid"
            for row in self.verify_result:
                if row["status"].lower() == "invalid":
                    self.verdict = "invalid"
        else:
            self.verdict = self.verify_result

        if self.verdict == "valid":
            try:
                unwrapped_file = self._unwrap_file(cleartext)
            except Exception as e:
                logger.exception(e)
            else:
                self.metadata = self._retrtieve_metadata(unwrapped_file)
                self.attachments = unwrapped_file.get("data", {}).get("attachments") or []

    def _retrtieve_metadata(self, data):
        md = data["data"].copy()
        md.pop("attachments", None)
        return md

    def _unwrap_file(self, content):
        """
        Warning: it's unreliable but quick
        """
        def unwrap_it(what):
            if isinstance(what, str):
                # wrapped something
                if what.count(":") >= 2:
                    uuidvalue, vtype, val = what.split(":", maxsplit=2)
                    if len(uuidvalue) == len("6cdb27f1-a46e-4dea-b1af-3b3faf7d983d"):
                        if vtype == "string":
                            return str(val)
                        elif vtype == "boolean":
                            return True if val.lower() == "true" else False
                        elif vtype == "number":
                            return int(val)
                    else:
                        return what
            elif isinstance(what, list):
                return [
                    unwrap_it(x) for x in what
                ]
            elif isinstance(what, dict):
                return {
                    k: unwrap_it(v)
                    for k, v
                    in what.items()
                }
            else:
                return what

        wrapped = json.loads(content)
        return unwrap_it(wrapped)

    def _verify_file(self, file_content):
        resp = requests.post(
            config.OA_VERIFY_API_URL,
            files={
                "file": file_content,
            }
        )
        if resp.status_code == 200:
            return resp.json()
        elif resp.status_code == 400:
            logger.warning("OA verify: %s %s", resp.status_code, resp.json())
            return "wrong-file"
        else:
            logger.warning(
                "%s resp from the OA Verify endpoint - %s",
                resp.status_code, resp.content
            )
            return "error"

    def _parse_and_verify_qrcode(self, the_code):
        """
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

        Note we catch all exceptions one layer above, so no need to do it here

        """
        components = urllib.parse.urlparse(the_code)
        params = urllib.parse.parse_qs(components.query)
        req = json.loads(params["q"][0])
        if req["type"].upper() == "DOCUMENT":
            uri = req["payload"]["uri"]
            key = req["payload"]["key"]  # it's always AES
            # this will contain fields cipherText, iv, tag, type
            logger.info("Retrieving document %s", uri)
            document_info = requests.get(uri).json()["document"]

            cp = AESCipher(key)
            cleartext_b64 = cp.decrypt(
                document_info["iv"],
                document_info["tag"],
                document_info["cipherText"],
            ).decode("utf-8")
            cleartext = base64.b64decode(cleartext_b64)

            logger.info("Unpacking document %s", params["q"][0])

            self._unpack_and_verify_cleartext(cleartext)

        return False
