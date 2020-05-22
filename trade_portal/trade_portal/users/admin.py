from django.contrib import admin
from django.contrib.auth import admin as auth_admin
from django.contrib.auth import get_user_model

from trade_portal.users.forms import UserChangeForm, UserCreationForm

User = get_user_model()


@admin.register(User)
class UserAdmin(auth_admin.UserAdmin):
    form = UserChangeForm
    add_form = UserCreationForm
    list_display = [
        "username", "email",
        "first_name", "last_name", "is_staff", "is_superuser",
    ]
    list_filter = ["is_staff", "is_superuser"]
    search_fields = ["username", "email"]
