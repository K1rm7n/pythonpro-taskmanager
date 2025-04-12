from django.contrib import admin
from .models import File, FileAccess


@admin.register(File)
class FileAdmin(admin.ModelAdmin):
    list_display = ('name', 'content_type', 'size', 'project', 'task', 'uploaded_by', 'uploaded_at')
    list_filter = ('content_type', 'uploaded_at')
    search_fields = ('name', 'project__title', 'task__title', 'uploaded_by__username')
    raw_id_fields = ('project', 'task', 'uploaded_by')
    date_hierarchy = 'uploaded_at'
    
    def get_queryset(self, request):
        """Prefetch related objects to reduce DB queries"""
        return super().get_queryset(request).select_related('project', 'task', 'uploaded_by')


@admin.register(FileAccess)
class FileAccessAdmin(admin.ModelAdmin):
    list_display = ('file', 'user', 'accessed_at')
    list_filter = ('accessed_at',)
    search_fields = ('file__name', 'user__username')
    raw_id_fields = ('file', 'user')
    date_hierarchy = 'accessed_at'
