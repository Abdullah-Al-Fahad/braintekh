from django.contrib import admin
from unfold.admin import ModelAdmin
from import_export.admin import ImportExportModelAdmin
from unfold.contrib.import_export.forms import ExportForm, ImportForm, SelectableFieldsExportForm
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import User


@admin.register(User)
class CustomUserAdmin(BaseUserAdmin, ModelAdmin, ImportExportModelAdmin):
    export_form_class = SelectableFieldsExportForm
    """
    Admin panel configuration for the custom User model.
    Uses the decorator pattern — no separate admin.site.register() call needed.
    """

    model = User
    ordering = ("email",)
    list_display = ("email", "first_name", "last_name", "role", "is_email_verified", "is_active", "is_staff")
    list_filter = ("role", "is_email_verified", "is_active", "is_staff")
    search_fields = ("email", "first_name", "last_name")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_("Personal Info"), {"fields": ("first_name", "last_name")}),
        (_("Platform Info"), {"fields": ("role", "is_email_verified")}),
        (_("Permissions"), {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        (_("Important Dates"), {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "first_name", "last_name", "password1", "password2", "role", "is_staff", "is_active"),
        }),
    )
