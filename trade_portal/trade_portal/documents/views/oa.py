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
        return HttpResponse(obj.ciphertext, content_type='text/plain')
