from django.contrib import admin

from .models import VerificationAttempt, Metric


@admin.register(VerificationAttempt)
class VerificationAttemptAdmin(admin.ModelAdmin):
    list_display = ("created_at", "type", "geo_info", "document")
    raw_id_fields = ("document",)
    list_filter = ("type",)


@admin.register(Metric)
class MetricAdmin(admin.ModelAdmin):
    list_display = ('name', 'value')
