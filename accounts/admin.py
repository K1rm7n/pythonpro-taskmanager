from django.contrib import admin
from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'position', 'phone', 'date_of_birth', 'created_at')
    search_fields = ('user__username', 'user__email', 'position', 'phone')
    list_filter = ('created_at',)
    raw_id_fields = ('user',)
