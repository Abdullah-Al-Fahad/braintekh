from django.contrib import admin
from .models import Category, Project, ProjectTeamMember, ProjectDocument, CollaborationRequest

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)

class ProjectTeamMemberInline(admin.TabularInline):
    model = ProjectTeamMember
    extra = 1

class ProjectDocumentInline(admin.TabularInline):
    model = ProjectDocument
    extra = 1

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'sponsor', 'status', 'funding_goal', 'raised_amount', 'created_at')
    list_filter = ('status', 'categories')
    search_fields = ('title', 'sponsor__user__email', 'sponsor__legal_company_name')
    inlines = [ProjectTeamMemberInline, ProjectDocumentInline]
    filter_horizontal = ('categories',)

@admin.register(CollaborationRequest)
class CollaborationRequestAdmin(admin.ModelAdmin):
    list_display = ('project', 'investor', 'status', 'proposed_budget', 'nda_signed', 'created_at')
    list_filter = ('status', 'nda_signed')
    search_fields = ('project__title', 'investor__user__email')
    readonly_fields = ('created_at', 'updated_at')
