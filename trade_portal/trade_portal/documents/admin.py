from django.contrib import admin

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
    list_display = (
        'business_id', 'type', 'bid_prefix', 'clear_business_id',
        'name', 'country',
    )


@admin.register(OaDetails)
class OaDetailsAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_for', 'uri', 'key', 'url_repr')


class DocumentHistoryItemInlineAdmin(admin.TabularInline):
    model = DocumentHistoryItem
    extra = 0
    fields = ['created_at', 'message', 'linked_obj_id', 'related_file']


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'status', 'type', 'importing_country')
    list_filter = ('status', 'type')
    inlines = [DocumentHistoryItemInlineAdmin]


@admin.register(DocumentFile)
class DocumentFileAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'doc', 'file', 'size')


@admin.register(NodeMessage)
class NodeMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'created_at', 'document', 'sender_ref', 'body')
