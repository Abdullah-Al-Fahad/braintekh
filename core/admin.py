from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Banner

@admin.register(Banner)
class BannerAdmin(ModelAdmin):
    list_display = ('title', 'tag', 'role', 'is_active', 'created_at')
    list_filter = ('is_active', 'role')
    search_fields = ('title', 'subtitle', 'tag')
