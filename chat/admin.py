from django.contrib import admin
from .models import ChatRoom, Message, UserChatStatus


@admin.register(ChatRoom)
class ChatRoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'is_project_room', 'project', 'created_at')
    list_filter = ('is_project_room', 'created_at')
    search_fields = ('name', 'project__title')
    raw_id_fields = ('project',)
    date_hierarchy = 'created_at'


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('sender', 'room', 'is_read', 'timestamp')
    list_filter = ('is_read', 'timestamp')
    search_fields = ('content', 'sender__username', 'room__name')
    raw_id_fields = ('room', 'sender')
    filter_horizontal = ('mentions',)
    date_hierarchy = 'timestamp'


@admin.register(UserChatStatus)
class UserChatStatusAdmin(admin.ModelAdmin):
    list_display = ('user', 'room', 'last_visited')
    search_fields = ('user__username', 'room__name')
    raw_id_fields = ('user', 'room', 'last_read_message')
    date_hierarchy = 'last_visited'
