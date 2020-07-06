import json

from django.http import HttpResponse, Http404
from django.views.generic import View

from trade_portal.documents.models import OaDetails


class OaCyphertextRetrieve(View):
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
            from trade_portal.documents.services import AESCipher
            try:
                cp = AESCipher(self.request.GET.get("key"))
                result["document"]["cleartext"] = cp.decrypt(
                    obj.iv_base64,
                    obj.tag_base64,
                    obj.ciphertext,
                ).decode("utf-8")
            except Exception as e:
                result["document"]["cleartext_error"] = str(e)
        return HttpResponse(json.dumps(result), content_type='application/json')
