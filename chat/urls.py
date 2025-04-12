from django.urls import path
from . import views

urlpatterns = [
    path('', views.chat_room_view, name='chat-room'),
    path('<int:room_id>/', views.chat_room_view, name='chat-room'),
    path('project/<int:project_id>/', views.create_project_chat, name='project-chat'),
    path('create/', views.create_custom_chat, name='create-chat'),
]
