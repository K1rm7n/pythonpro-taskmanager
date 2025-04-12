from django.urls import path
from . import views

urlpatterns = [
    path('project/', views.project_analytics_view, name='project-analytics'),
    path('team/', views.team_analytics_view, name='team-analytics'),
]
