import boto3
import logging

from mozilla_django_oidc.auth import OIDCAuthenticationBackend

logger = logging.getLogger(__name__)


class MyOIDCAB(OIDCAuthenticationBackend):
    """
    Claims are:
    {
        'sub': '462c73c4-380d-494c-bab0-778b34bb543e',
        'custom:roles': '[reporting_party,gov_admin]',
        'email_verified': 'false',
        'name': 'xxx',
        'phone_number_verified': 'true',
        'phone_number': '+xxx',
        'email': 'xx@xx.xx',
        'username': 'xx'
    }
    """

    def get_username(self, claims):
        """Generate username based on claims."""
        return claims.get('email')

    def _fill_user(self, user, claims):
        # access roles
        roles = claims.get("custom:roles", "").replace(
            "[", ""
        ).replace(
            "]", ""
        ).split(",") or []
        if "gov_admin" in roles:
            user.is_staff = True
        if "superuser" in roles:
            user.is_staff = True
            user.is_superuser = True
        if "gov_admin" not in roles and "superuser" not in roles:
            user.is_staff = False
            user.is_superuser = False
        user.save()

    def create_user(self, claims):
        """Return object for a newly created user account."""
        email = claims.get('email')
        username = self.get_username(claims)
        user = self.UserModel.objects.create_user(username, email)
        self._fill_user(user, claims)
        self.request.session["email_verified"] = (
            claims.get("email_verified") == "true"
        )
        return user

    def update_user(self, user, claims):
        """Update existing user with new claims, if necessary save, and return user"""
        self._fill_user(user, claims)
        return user
