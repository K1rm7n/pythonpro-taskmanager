from django.urls import path
from . import views

urlpatterns = [
    path('register/', views.SignUpView.as_view(), name='register'),
    path('profile/', views.profile_view, name='profile'),
]
