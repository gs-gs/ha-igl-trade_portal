import requests

from constance import config
from django.views.generic import TemplateView


class OaVerificationView(TemplateView):
    template_name = "oa_verify/verification.html"
    verify_result = None
    verdict = None

    def get_context_data(self, *args, **kwargs):
        c = super().get_context_data(*args, **kwargs)
        c['verify_result'] = self.verify_result
        c['verdict'] = self.verdict
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
        return super().get(request, *args, **kwargs)

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
