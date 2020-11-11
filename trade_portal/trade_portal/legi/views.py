import logging

from django.views.generic import View
from django.http import JsonResponse
from django.utils.html import escape

from trade_portal.legi.abr import fetch_abn_info


logger = logging.getLogger(__name__)


class AbnLookupView(View):
    def get(self, request, *args, **kwargs):
        abn = request.GET.get("abn")
        try:
            int(abn)
        except (ValueError, TypeError):
            abn = None

        if not abn or len(abn) != 11:
            return JsonResponse(
                {
                    "status": "fail",
                    "msg": "Wrong ABN format",
                }
            )

        try:
            abn_info = fetch_abn_info(abn)
        except Exception as e:
            logger.exception(e)
            return JsonResponse(
                {
                    "status": "fail",
                    "snippet": "(no data about this ABN is available)",
                    "abn": abn,
                }
            )
        else:
            try:
                abn_info.pop("BusinessName", None)
            except Exception as e:
                logger.exception(e)
            snippet = abn_info.get("Message") or "".join(
                f"<p><strong>{escape(a)}:</strong><span>{escape(b)}</span></p>\n"
                for a, b in abn_info.items()
                if b
            )
            status = "ok" if not abn_info.get("Message") else "not_found"
            resp = abn_info.copy()
            resp.update({"snippet": snippet, "status": status})
            return JsonResponse(resp)
