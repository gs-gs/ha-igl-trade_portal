from allauth.account.forms import SignupForm
from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model, forms as auth_forms
from django.utils.translation import gettext_lazy as _

from trade_portal.users.models import OrgRoleRequest, OrganisationAuthToken
from trade_portal.users.tasks import (
    notify_about_new_user_created, notify_role_requested,
)

User = get_user_model()


class CustomSignupForm(SignupForm):
    first_name = forms.CharField(label=_("First name"))
    last_name = forms.CharField(label=_("Last name"))
    initial_business_id = forms.CharField(
        label=settings.BID_NAME,
        help_text=_("This value will be verified")
    )
    mobile_number = forms.CharField(max_length=50, label=_("Mobile phone number"))

    class Meta:
        model = User
        fields = [
            "ignored",
            'first_name', 'last_name', 'initial_business_id',
            'email', 'password1', 'password2',
            'mobile_number',
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["initial_business_id"].label = _("Your business") + settings.BID_NAME
        self.fields["password1"].label = _("Choose a password")
        self.fields["email"].label = _("Your business email address")

    def clean_mobile_number(self):
        phone = (self.cleaned_data.get("mobile_number") or "").strip().replace(" ", "")
        phone = phone.lstrip("0")
        if not phone.startswith("61") and not phone.startswith("+61"):
            phone = "+61" + phone
        if not phone.startswith("+"):
            phone = "+" + phone
        # questionable
        already_confirmed_numbers = User.objects.filter(
            verified_mobile_number=phone
        ).count()
        if already_confirmed_numbers >= 3:
            raise forms.ValidationError(
                _("Entered phone number is already used in maximal number of accounts")
            )
        return phone

    def save(self, *args, **kwargs):
        user = super().save(*args, **kwargs)
        user.mobile_number = self.cleaned_data.get("mobile_number") or ""
        user.initial_business_id = self.cleaned_data.get("initial_business_id") or ""
        user.save()
        notify_about_new_user_created.apply_async(
            [user.pk],
            countdown=5
        )
        return user


class UserChangeForm(forms.ModelForm):
    first_name = forms.CharField(widget=forms.TextInput(attrs={'placeholder': _('First name')}))
    last_name = forms.CharField(widget=forms.TextInput(attrs={'placeholder': _('Last name')}))
    mobile_number = forms.CharField(max_length=50, label=_("Mobile phone number"))

    class Meta:
        model = User
        fields = [
            "first_name", "last_name",
            "mobile_number",
        ]


class UserCreationForm(auth_forms.UserCreationForm):

    class Meta(auth_forms.UserCreationForm.Meta):
        model = User
        fields = (
            'first_name', 'last_name', 'email', 'password1', 'password2',
            'mobile_number',
        )


class RoleRequestForm(forms.ModelForm):
    class Meta:
        model = OrgRoleRequest
        fields = ('org', 'role', 'evidence')

    def __init__(self, user, *args, **kwargs):
        self.user = user
        super().__init__(*args, **kwargs)
        self.fields["org"].choices = (
            (x.pk, str(x))
            for x in self.user.direct_orgs
        )
        self.fields["evidence"].help_text = _(
            "This field is optional but uploading it will help the review. "
            "Please make sure the image uploaded is clearly readable."
        )

    def save(self, *args, **kwargs):
        self.instance.created_by = self.user
        req = super().save(*args, **kwargs)
        notify_role_requested.apply_async(
            [req.pk],
            countdown=5
        )
        return req


class TokenCreateForm(forms.ModelForm):
    class Meta:
        model = OrganisationAuthToken
        fields = ('readable_name', )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user")
        self.current_org = kwargs.pop("current_org")
        super().__init__(*args, **kwargs)

    def save(self, *args, **kwargs):
        # https://github.com/encode/django-rest-framework/blob/master/rest_framework/authtoken/models.py
        self.instance.user = self.user
        self.instance.org = self.current_org
        return super().save(*args, **kwargs)
