from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from import_export.admin import ImportExportModelAdmin
from unfold.contrib.import_export.forms import ExportForm, ImportForm, SelectableFieldsExportForm
from .models import Category, Project, ProjectTeamMember, ProjectDocument, CollaborationRequest

@admin.register(Category)
class CategoryAdmin(ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

class ProjectTeamMemberInline(TabularInline):
    model = ProjectTeamMember
    extra = 1

class ProjectDocumentInline(TabularInline):
    model = ProjectDocument
    extra = 1

@admin.register(Project)
class ProjectAdmin(ModelAdmin, ImportExportModelAdmin):
    export_form_class = SelectableFieldsExportForm
    list_display = ('title', 'sponsor', 'status', 'funding_goal', 'raised_amount', 'created_at')
    list_filter = ('status', 'categories')
    search_fields = ('title', 'sponsor__user__email', 'sponsor__legal_company_name')
    inlines = [ProjectTeamMemberInline, ProjectDocumentInline]
    filter_horizontal = ('categories',)

@admin.register(CollaborationRequest)
class CollaborationRequestAdmin(ModelAdmin, ImportExportModelAdmin):
    export_form_class = SelectableFieldsExportForm
    list_display = ('project', 'investor', 'status', 'proposed_budget', 'nda_signed', 'created_at')
    list_filter = ('status', 'nda_signed')
    search_fields = ('project__title', 'investor__user__email')
    readonly_fields = ('created_at', 'updated_at')
    actions = ["approve_request", "reject_request"]

    @admin.action(description="Approve selected Requests")
    def approve_request(self, request, queryset):
        from .models import CollaborationRequestStatus
        queryset.update(status=CollaborationRequestStatus.APPROVED)

    @admin.action(description="Reject selected Requests")
    def reject_request(self, request, queryset):
        from .models import CollaborationRequestStatus
        queryset.update(status=CollaborationRequestStatus.REJECTED)
