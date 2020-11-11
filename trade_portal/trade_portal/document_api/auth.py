from django.utils.translation import gettext as _
from rest_framework import exceptions
from rest_framework.authentication import TokenAuthentication

from trade_portal.users.models import OrganisationAuthToken


class OurTokenAuthentication(TokenAuthentication):
    model = OrganisationAuthToken

    def authenticate_credentials(self, key):
        model = self.get_model()
        try:
            token = model.objects.select_related("user").get(access_token=key)
        except model.DoesNotExist:
            raise exceptions.AuthenticationFailed(_("Invalid token."))

        if not token.user.is_active:
            raise exceptions.AuthenticationFailed(_("User inactive or deleted."))

        return (token.user, token)
