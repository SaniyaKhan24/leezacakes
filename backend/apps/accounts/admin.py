from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import AccountVerificationToken, Address, User


@admin.register(User)
class AccountUserAdmin(UserAdmin):
    ordering = ("email",)
    list_display = (
        "email",
        "first_name",
        "last_name",
        "is_active",
        "is_email_verified",
        "is_staff",
    )
    search_fields = ("email", "first_name", "last_name")
    fieldsets = UserAdmin.fieldsets + (
        ("Account", {"fields": ("phone_number", "is_email_verified")}),
    )
    add_fieldsets = ((None, {"classes": ("wide",), "fields": ("email", "password1", "password2")}),)


@admin.register(Address)
class AddressAdmin(admin.ModelAdmin):
    list_display = ("user", "label", "city", "country_code", "is_default")
    search_fields = ("user__email", "recipient_name", "city")
    list_filter = ("country_code", "is_default")


@admin.register(AccountVerificationToken)
class AccountVerificationTokenAdmin(admin.ModelAdmin):
    list_display = ("user", "purpose", "expires_at", "used_at", "created_at")
    readonly_fields = ("token_digest",)
