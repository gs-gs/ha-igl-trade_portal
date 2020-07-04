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
        # by default the ciphertext is base64-encoded
        if self.request.GET.get("key"):
            from trade_portal.documents.services import AESCipher
            cp = AESCipher(self.request.GET.get("key"))
            return HttpResponse(cp.decrypt(obj.ciphertext), content_type='text/plain')
        return HttpResponse(obj.ciphertext, content_type='text/plain')
