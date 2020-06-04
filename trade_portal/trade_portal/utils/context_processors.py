from django.conf import settings


def settings_context(_request):
    if _request.user.is_authenticated:
        # for authenticated users
        # we return the org stored in the session
        # or first available otherwise
        current_org = _request.user.get_current_org(_request.session)
    else:
        current_org = None
    return {
        "ICL_APP_COUNTRY": settings.ICL_APP_COUNTRY,
        "current_org": current_org
    }
