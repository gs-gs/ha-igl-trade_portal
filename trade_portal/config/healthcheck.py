from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse
from django.views import View


class HealthcheckView(View):
    def get(self, request):
        data = {
            "status": "ok",
            "BUILD_REFERENCE": settings.BUILD_REFERENCE,
            "CONFIGURATION_REFERENCE": settings.CONFIGURATION_REFERENCE,
            "APP_REFERENCE": settings.APP_REFERENCE,
            "canary_task": cache.get("canary-task-last-run"),
        }
        return JsonResponse(data)
