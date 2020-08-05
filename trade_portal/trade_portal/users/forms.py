from allauth.account.forms import SignupForm
from django import forms
from django.conf import settings
from django.contrib.auth import get_user_model, forms as auth_forms

from trade_portal.users.models import OrgRoleRequest

User = get_user_model()


class CustomSignupForm(SignupForm):
    first_name = forms.CharField(label="First name")
    last_name = forms.CharField(label="Last name")
    initial_business_id = forms.CharField(
        label=settings.BID_NAME,
        help_text="This value will be verified"
    )
    mobile_number = forms.CharField(max_length=50, label="Mobile phone number")

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
        self.fields["initial_business_id"].label = f"Your business {settings.BID_NAME}"
        self.fields["password1"].label = "Choose a password"

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
                "Entered phone number is already used in maximal number of accounts"
            )
        return phone

    def save(self, *args, **kwargs):
        user = super().save(*args, **kwargs)
        user.mobile_number = self.cleaned_data.get("mobile_number") or ""
        user.initial_business_id = self.cleaned_data.get("initial_business_id") or ""
        user.save()
        return user


class UserChangeForm(forms.ModelForm):
    first_name = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'First name'}))
    last_name = forms.CharField(widget=forms.TextInput(attrs={'placeholder': 'Last name'}))
    mobile_number = forms.CharField(max_length=50, label="Mobile phone number")

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

    def save(self, *args, **kwargs):
        self.instance.created_by = self.user
        return super().save(*args, **kwargs)
