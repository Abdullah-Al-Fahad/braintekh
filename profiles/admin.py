from django.contrib import admin

from .models import Document, Industry, InvestorProfile, SponsorProfile


@admin.register(Industry)
class IndustryAdmin(admin.ModelAdmin):
    list_display = ("name",)
    search_fields = ("name",)


@admin.register(InvestorProfile)
class InvestorProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "investor_type", "country", "verification_status", "created_at")
    list_filter = ("investor_type", "verification_status", "country")
    search_fields = ("user__email", "user__first_name", "user__last_name")
    readonly_fields = ("created_at", "updated_at")
    filter_horizontal = ("industries",)


@admin.register(SponsorProfile)
class SponsorProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "legal_company_name", "country", "verification_status", "created_at")
    list_filter = ("verification_status", "country")
    search_fields = ("user__email", "legal_company_name", "registration_number")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ("user", "document_type", "created_at")
    list_filter = ("document_type",)
    search_fields = ("user__email",)
    readonly_fields = ("created_at", "updated_at")
