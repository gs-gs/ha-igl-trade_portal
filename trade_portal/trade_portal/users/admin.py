from django.contrib import admin
from django.contrib.auth import admin as auth_admin
from django.contrib.auth import get_user_model

from trade_portal.users.models import Organisation, OrgMembership
from trade_portal.users.forms import UserChangeForm, UserCreationForm

User = get_user_model()


@admin.register(User)
class UserAdmin(auth_admin.UserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    list_display = [
        "pk", "username", "email",
        "first_name", "last_name", "is_staff", "is_superuser",
    ]
    list_filter = ["is_staff", "is_superuser"]
    search_fields = ["username", "email"]


@admin.register(Organisation)
class OrganisationAdmin(admin.ModelAdmin):
    list_display = ("pk", "name", "type", "business_id")


@admin.register(OrgMembership)
class OrgMembershipAdmin(admin.ModelAdmin):
    list_display = ("pk", "org", "user", "since", "role")
