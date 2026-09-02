from django.contrib import admin
from .models import Notification, Message

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'title', 'notification_type', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read')
    search_fields = ('recipient__email', 'title', 'message')
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'recipient', 'created_at')
    search_fields = ('sender__email', 'recipient__email', 'content')
    readonly_fields = ('created_at', 'updated_at')
