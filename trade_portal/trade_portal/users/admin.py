from django.contrib import admin
from django.contrib.auth import admin as auth_admin
from django.contrib.auth import get_user_model

from trade_portal.users.models import (
    Organisation, OrgMembership, OrgRoleRequest,
)
from trade_portal.users.forms import UserChangeForm

User = get_user_model()


@admin.register(User)
class UserAdmin(auth_admin.UserAdmin):
    form = UserChangeForm
    # add_form = UserCreationForm
    list_display = [
        "pk", "username", "email",
        "first_name", "last_name", "is_staff", "is_superuser",
    ]
    list_filter = ["is_staff", "is_superuser"]
    search_fields = ["username", "email"]
    fieldsets = auth_admin.UserAdmin.fieldsets + (
        ("Business Data", {'fields': ('mobile_number', 'initial_business_id')}),
    )


@admin.register(Organisation)
class OrganisationAdmin(admin.ModelAdmin):
    list_display = (
        "pk", "name", "business_id", "dot_separated_id",
        "is_trader", "is_chambers", "is_regulator"
    )


@admin.register(OrgMembership)
class OrgMembershipAdmin(admin.ModelAdmin):
    list_display = ("pk", "org", "user", "since", "role")


@admin.register(OrgRoleRequest)
class OrgRoleRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "org", "role", "status")
