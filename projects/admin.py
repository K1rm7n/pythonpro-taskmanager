from django.contrib import admin
from .models import Project, Task, Comment, TaskHistory


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'status', 'owner', 'start_date', 'end_date', 'created_at')
    list_filter = ('status', 'start_date', 'created_at')
    search_fields = ('title', 'description', 'owner__username')
    filter_horizontal = ('members',)
    date_hierarchy = 'created_at'


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('title', 'project', 'status', 'priority', 'assignee', 'due_date', 'created_at')
    list_filter = ('status', 'priority', 'due_date', 'created_at')
    search_fields = ('title', 'description', 'assignee__username', 'project__title')
    raw_id_fields = ('project', 'assignee', 'created_by', 'parent_task')
    date_hierarchy = 'created_at'


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ('task', 'author', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('text', 'author__username', 'task__title')
    raw_id_fields = ('task', 'author')
    date_hierarchy = 'created_at'


@admin.register(TaskHistory)
class TaskHistoryAdmin(admin.ModelAdmin):
    list_display = ('task', 'user', 'changed_field', 'timestamp')
    list_filter = ('timestamp', 'changed_field')
    search_fields = ('task__title', 'user__username', 'old_value', 'new_value')
    raw_id_fields = ('task', 'user')
    date_hierarchy = 'timestamp'
