import json

from django.http import HttpResponse, Http404
from django.views.generic import View
from django.utils.translation import gettext as _

from trade_portal.documents.models import OaDetails


class AllowCORSMixin(object):

    def add_access_control_headers(self, response):
        response["Access-Control-Allow-Origin"] = "*"
        response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response["Access-Control-Max-Age"] = "1000"
        response["Access-Control-Allow-Headers"] = "X-Requested-With, Content-Type"

    def options(self, request, *args, **kwargs):
        response = HttpResponse()
        self.add_access_control_headers(response)
        return response


class OaCyphertextRetrieve(AllowCORSMixin, View):
    def get(self, *args, **kwargs):
        try:
            obj = OaDetails.objects.get(
                id=self.kwargs["key"]
            )
        except Exception:
            raise Http404()

        result = {
            "document": {
                "cipherText": obj.ciphertext,
                "iv": obj.iv_base64,  # "5O0HYHcYhTzB/Xmt",
                "tag": obj.tag_base64,  # "Yo1q82WRHFQuKUSYHgnawQ==",
                "type": "OPEN-ATTESTATION-TYPE-1"
            }
        }
        # by default the ciphertext is base64-encoded
        if self.request.GET.get("key"):
            from trade_portal.documents.services.lodge import AESCipher
            try:
                cp = AESCipher(self.request.GET.get("key"))
                result["document"]["cleartext"] = cp.decrypt(
                    obj.iv_base64,
                    obj.tag_base64,
                    obj.ciphertext,
                ).decode("utf-8")
            except Exception as e:
                result["document"]["cleartext_error"] = str(e)

        response = HttpResponse(json.dumps(result), content_type='application/json')
        self.add_access_control_headers(response)
        return response
