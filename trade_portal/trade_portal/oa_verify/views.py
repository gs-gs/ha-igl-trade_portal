import json
import logging

import requests

from constance import config
from django.views.generic import TemplateView

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
        the_file = request.FILES["oa_file"]
        value = the_file.read()
        self.verify_result = self._verify_file(value)
        if self.verify_result and self.verify_result != "error":
            self.verdict = "valid"
            for row in self.verify_result:
                if row["status"].lower() == "invalid":
                    self.verdict = "invalid"
        else:
            self.verdict = "error"

        if self.verdict == "valid":
            try:
                unwrapped_file = self._unwrap_file(value)
            except Exception as e:
                logger.exception(e)
            else:
                self.metadata = self._retrtieve_metadata(unwrapped_file)
                self.attachments = unwrapped_file.get("data", {}).get("attachments") or []

        return super().get(request, *args, **kwargs)

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
        if resp.status_code != 200:
            return "error"
        else:
            return resp.json()
