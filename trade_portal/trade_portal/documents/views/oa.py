from django.http import HttpResponse, Http404
from django.views.generic import View

from trade_portal.documents.models import OaUrl


class OaCyphertextRetrieve(View):
    def get(self, *args, **kwargs):
        try:
            obj = OaUrl.objects.get(
                id=self.kwargs["key"]
            )
        except Exception:
            raise Http404()
        return HttpResponse(obj.ciphertext, content_type='text/plain')
