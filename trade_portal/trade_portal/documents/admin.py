from django.contrib import admin

from .models import (
    FTA, Party,
    Document, DocumentFile,
    NodeMessage,
)


@admin.register(FTA)
class FTAAdmin(admin.ModelAdmin):
    list_display = ('name',)


@admin.register(Party)
class PartyAdmin(admin.ModelAdmin):
    list_display = ('business_id', 'name', 'country')


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'type', 'importing_country', 'status')
    list_filter = ('status', 'type', 'importing_country')


@admin.register(DocumentFile)
class DocumentFileAdmin(admin.ModelAdmin):
    list_display = ('created_at', 'doc', 'file', 'size')


@admin.register(NodeMessage)
class NodeMessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'created_at', 'document', 'sender_ref', 'body')
