from django.contrib import admin
from .models import UploadedFile, UploadStatus

@admin.register(UploadStatus)
class UploadStatusAdmin(admin.ModelAdmin):
    list_display = ('process', 'date', 'status', 'uploaded_file', 'updated_at')
    list_filter = ('status', 'process', 'date')
    search_fields = ('process',)

@admin.register(UploadedFile)
class UploadedFileAdmin(admin.ModelAdmin):
    list_display = ('process', 'uploaded_at', 'user', 'file')
