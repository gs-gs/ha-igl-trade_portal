from django.conf import settings


def settings_context(_request):
    return {
        "ICL_APP_COUNTRY": settings.ICL_APP_COUNTRY,
        "CHAMBERS_ORG_NAME": settings.CHAMBERS_ORG_NAME,
        "CHAMBERS_ORG_ID": settings.CHAMBERS_ORG_ID,
    }
