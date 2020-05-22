from django.contrib import admin

from .models import FeedbackItem


@admin.register(FeedbackItem)
class FeedbackItemAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'user', 'email')
    search_fields = ('text', 'email', 'contact')
