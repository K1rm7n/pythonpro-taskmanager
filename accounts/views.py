from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.urls import reverse_lazy
from django.views.generic import CreateView, UpdateView
from django.contrib.auth.mixins import LoginRequiredMixin
from .forms import CustomUserCreationForm, UserProfileForm, UserForm
from .models import UserProfile
import logging

# Set up logger
logger = logging.getLogger('taskmanager')


class SignUpView(CreateView):
    """User registration view"""
    template_name = 'accounts/register.html'
    form_class = CustomUserCreationForm
    success_url = reverse_lazy('login')
    
    def form_valid(self, form):
        response = super().form_valid(form)
        logger.info(f"New user registered: {self.object.username}")
        messages.success(self.request, 'Реєстрація успішна! Тепер ви можете увійти в систему.')
        return response


@login_required
def profile_view(request):
    """User profile view"""
    if request.method == 'POST':
        user_form = UserForm(request.POST, instance=request.user)
        profile_form = UserProfileForm(request.POST, request.FILES, instance=request.user.profile)
        
        if user_form.is_valid() and profile_form.is_valid():
            user_form.save()
            profile_form.save()
            logger.info(f"User {request.user.username} updated their profile")
            messages.success(request, 'Ваш профіль успішно оновлено!')
            return redirect('profile')
        else:
            messages.error(request, 'Будь ласка, виправте помилки у формі.')
    else:
        user_form = UserForm(instance=request.user)
        profile_form = UserProfileForm(instance=request.user.profile)
    
    context = {
        'user_form': user_form,
        'profile_form': profile_form
    }
    
    return render(request, 'accounts/profile.html', context)
