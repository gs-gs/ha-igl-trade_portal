from . import Env

env = Env()

SESSION_COOKIE_NAME = "tr-prt-sess"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
    "trade_portal.users.backends.MyOIDCAB",
]
AUTH_USER_MODEL = "users.User"
LOGIN_REDIRECT_URL = "/"
LOGOUT_REDIRECT_URL = "/"
LOGIN_URL = "account_login"  # "oidc_authentication_init"

# OIDC
OIDC_RP_CLIENT_ID = env('ICL_OIDC_RP_CLIENT_ID', default='')
OIDC_RP_CLIENT_SECRET = env('ICL_OIDC_RP_CLIENT_SECRET', default='')
OIDC_OP_AUTHORIZATION_ENDPOINT = env(
    'ICL_OIDC_OP_AUTHORIZATION_ENDPOINT',
    default="http://please-fill-it/oauth2/authorize"
)
OIDC_OP_LOGOUT_ENDPOINT = env(
    'ICL_OIDC_OP_LOGOUT_ENDPOINT',
    default="http://please-fill-it/logout"
)
OIDC_OP_TOKEN_ENDPOINT = env(
    'ICL_OIDC_OP_TOKEN_ENDPOINT',
    default="http://please-fill-it/oauth2/token"
)
OIDC_OP_USER_ENDPOINT = env(
    'ICL_OIDC_OP_USER_ENDPOINT',
    default="http://please-fill-it/oauth2/userInfo"
)
OIDC_RP_SIGN_ALGO = "RS256"
OIDC_OP_JWKS_ENDPOINT = env(
    'ICL_OIDC_OP_JWKS_ENDPOINT',
    default="http://please-fill-it/.well-known/jwks.json"
)
OIDC_AUTH_REQUEST_EXTRA_PARAMS = {
    "scope": "openid email profile aws.cognito.signin.user.admin"
}

OIDC_STORE_ACCESS_TOKEN = True
OIDC_STORE_ID_TOKEN = True

if OIDC_RP_CLIENT_ID and OIDC_RP_CLIENT_SECRET:
    USE_COGNITO = True
else:
    USE_COGNITO = False


# django-allauth
# env.bool("DJANGO_ACCOUNT_ALLOW_REGISTRATION", True)
ACCOUNT_ALLOW_REGISTRATION = True
ACCOUNT_AUTHENTICATION_METHOD = "email"
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_EMAIL_VERIFICATION = "none"  # "mandatory"
ACCOUNT_ADAPTER = "trade_portal.users.adapters.AccountAdapter"
SOCIALACCOUNT_ADAPTER = "trade_portal.users.adapters.SocialAccountAdapter"
ACCOUNT_FORMS = {
    # 'login': 'allauth.account.forms.LoginForm',
    # 'signup': 'trade_portal.users.forms.CustomSignupForm',
    # 'add_email': 'allauth.account.forms.AddEmailForm',
    # 'change_password': 'allauth.account.forms.ChangePasswordForm',
    # 'set_password': 'allauth.account.forms.SetPasswordForm',
    # 'reset_password': 'allauth.account.forms.ResetPasswordForm',
    # 'reset_password_from_key': 'allauth.account.forms.ResetPasswordKeyForm',
    # 'disconnect': 'allauth.socialaccount.forms.DisconnectForm',
}
