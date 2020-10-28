from django.contrib import admin
from django.shortcuts import redirect

from .models import (
    FTA, Party,
    OaDetails, Document, DocumentFile, DocumentHistoryItem,
    NodeMessage,
)


@admin.register(FTA)
class FTAAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(Party)
class PartyAdmin(admin.ModelAdmin):
    search_fields = ('name', 'business_id')
    list_display = (
        'business_id', 'type', 'bid_prefix', 'clear_business_id',
        'name', 'country',
    )


@admin.register(OaDetails)
class OaDetailsAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_at', 'created_for', 'uri', 'key', 'url_repr', 'get_OA_file')

    def get_queryset(self, *args, **kwargs):
        qs = super().get_queryset(*args, **kwargs)
        qs = qs.select_related(
            'created_for',
        )
        return qs


class DocumentHistoryItemInlineAdmin(admin.TabularInline):
    model = DocumentHistoryItem
    extra = 0
    fields = ['created_at', 'message', 'linked_obj_id', 'related_file']


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = (
        'created_at', 'workflow_status', 'verification_status', 'status',
        'type', 'importing_country'
    )
    list_filter = ('status', 'type')
    inlines = [DocumentHistoryItemInlineAdmin]
    actions = ["reverify_document"]

    def reverify_document(self, request, qs):
        from .tasks import verify_own_document
        for obj in qs.all():
            verify_own_document.delay(obj.pk)
        return redirect(request.path_info)


@admin.register(DocumentFile)
class DocumentFileAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'doc', 'file', 'size')


@admin.register(NodeMessage)
class NodeMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'created_at', 'document', 'sender_ref', 'body')
