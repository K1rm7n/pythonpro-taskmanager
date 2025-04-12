from django.contrib import admin
from .models import ProjectStatistics, UserActivity


@admin.register(ProjectStatistics)
class ProjectStatisticsAdmin(admin.ModelAdmin):
    list_display = ('project', 'date', 'total_tasks', 'completed_tasks', 'overdue_tasks')
    list_filter = ('date',)
    search_fields = ('project__title',)
    raw_id_fields = ('project',)
    date_hierarchy = 'date'


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    list_display = ('user', 'date', 'tasks_created', 'tasks_completed', 'comments_added', 'hours_logged')
    list_filter = ('date',)
    search_fields = ('user__username', 'user__email')
    raw_id_fields = ('user',)
    date_hierarchy = 'date'
