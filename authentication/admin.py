from django.contrib import admin
from .models import OTPRecord


@admin.register(OTPRecord)
class OTPRecordAdmin(admin.ModelAdmin):
    list_display = ("user", "purpose", "is_used", "created_at")
    list_filter = ("purpose", "is_used")
    search_fields = ("user__email",)
    readonly_fields = ("code", "user", "purpose", "created_at", "updated_at")
    ordering = ("-created_at",)
