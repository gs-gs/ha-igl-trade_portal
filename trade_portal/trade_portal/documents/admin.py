from django.contrib import admin

from .models import (
    FTA, Party,
    OaUrl, Document, DocumentFile,
    NodeMessage,
)


@admin.register(FTA)
class FTAAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(Party)
class PartyAdmin(admin.ModelAdmin):
    list_display = ('business_id', 'name', 'country')


@admin.register(OaUrl)
class OaUrlAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_for', 'uri', 'key', 'url_repr')


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'status', 'type', 'importing_country', 'status')
    list_filter = ('status', 'type', 'importing_country')


@admin.register(DocumentFile)
class DocumentFileAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'doc', 'file', 'size')


@admin.register(NodeMessage)
class NodeMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'status', 'created_at', 'document', 'sender_ref', 'body')
