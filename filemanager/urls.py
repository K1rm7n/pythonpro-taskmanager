from django.urls import path
from . import views

urlpatterns = [
    path('', views.file_list_view, name='file-list'),
    path('upload/', views.file_upload_view, name='file-upload'),
    path('download/<int:file_id>/', views.file_download_view, name='file-download'),
    path('delete/<int:file_id>/', views.file_delete_view, name='file-delete'),
    path('api/get-tasks/', views.get_task_options, name='get-task-options'),
]
