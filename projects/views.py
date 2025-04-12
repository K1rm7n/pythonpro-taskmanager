from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse_lazy, reverse
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView
)
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse
from django.utils import timezone
from django.db import transaction

from .models import Project, Task, Comment, TaskHistory
from .forms import ProjectForm, TaskForm, TaskUpdateForm, CommentForm

import logging

# Set up logger
logger = logging.getLogger('taskmanager')


class ProjectListView(LoginRequiredMixin, ListView):
    """View to display user's projects"""
    model = Project
    template_name = 'projects/project_list.html'
    context_object_name = 'projects'
    paginate_by = 10
    
    def get_queryset(self):
        """Filter projects to show only those the user is a member of or owns"""
        return Project.objects.filter(
            Q(owner=self.request.user) | Q(members=self.request.user)
        ).distinct()


class ProjectDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """View to display project details"""
    model = Project
    template_name = 'projects/project_detail.html'
    context_object_name = 'project'
    
    def test_func(self):
        """Test if user has access to this project"""
        project = self.get_object()
        return self.request.user == project.owner or self.request.user in project.members.all()
    
    def get_context_data(self, **kwargs):
        """Add tasks to context"""
        context = super().get_context_data(**kwargs)
        project = self.get_object()
        
        # Get all tasks for this project
        context['todo_tasks'] = project.tasks.filter(status='todo')
        context['in_progress_tasks'] = project.tasks.filter(status='in_progress')
        context['review_tasks'] = project.tasks.filter(status='review')
        context['completed_tasks'] = project.tasks.filter(status='completed')
        
        return context


class ProjectCreateView(LoginRequiredMixin, CreateView):
    """View to create a new project"""
    model = Project
    form_class = ProjectForm
    template_name = 'projects/project_form.html'
    
    def get_form_kwargs(self):
        """Pass the current user to the form"""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        """Set the owner to the current user"""
        form.instance.owner = self.request.user
        response = super().form_valid(form)
        logger.info(f"User {self.request.user.username} created project: {form.instance.title}")
        messages.success(self.request, f'Проект "{form.instance.title}" успішно створено!')
        return response


class ProjectUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """View to update project details"""
    model = Project
    form_class = ProjectForm
    template_name = 'projects/project_form.html'
    
    def test_func(self):
        """Only the project owner can update it"""
        project = self.get_object()
        return self.request.user == project.owner
    
    def get_form_kwargs(self):
        """Pass the current user to the form"""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        """Handle successful form submission"""
        response = super().form_valid(form)
        logger.info(f"User {self.request.user.username} updated project: {form.instance.title}")
        messages.success(self.request, f'Проект "{form.instance.title}" успішно оновлено!')
        return response


class ProjectDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """View to delete a project"""
    model = Project
    template_name = 'projects/project_confirm_delete.html'
    success_url = reverse_lazy('project-list')
    
    def test_func(self):
        """Only the project owner can delete it"""
        project = self.get_object()
        return self.request.user == project.owner
    
    def delete(self, request, *args, **kwargs):
        """Log deletion and show success message"""
        project = self.get_object()
        project_title = project.title
        response = super().delete(request, *args, **kwargs)
        logger.info(f"User {self.request.user.username} deleted project: {project_title}")
        messages.success(self.request, f'Проект "{project_title}" успішно видалено!')
        return response


class TaskListView(LoginRequiredMixin, ListView):
    """View to display user's tasks"""
    model = Task
    template_name = 'projects/task_list.html'
    context_object_name = 'tasks'
    paginate_by = 12
    
    def get_queryset(self):
        """Filter tasks to show only those assigned to user or from user's projects"""
        user_tasks = Task.objects.filter(
            Q(assignee=self.request.user) | 
            Q(project__owner=self.request.user) |
            Q(project__members=self.request.user)
        ).distinct()
        
        # Apply filters if provided
        status_filter = self.request.GET.get('status')
        priority_filter = self.request.GET.get('priority')
        project_filter = self.request.GET.get('project')
        
        if status_filter and status_filter != 'all':
            user_tasks = user_tasks.filter(status=status_filter)
        
        if priority_filter and priority_filter != 'all':
            user_tasks = user_tasks.filter(priority=priority_filter)
            
        if project_filter and project_filter.isdigit():
            user_tasks = user_tasks.filter(project_id=project_filter)
            
        return user_tasks
    
    def get_context_data(self, **kwargs):
        """Add filter options to context"""
        context = super().get_context_data(**kwargs)
        context['projects'] = Project.objects.filter(
            Q(owner=self.request.user) | Q(members=self.request.user)
        ).distinct()
        
        # Get current filter values
        context['status_filter'] = self.request.GET.get('status', 'all')
        context['priority_filter'] = self.request.GET.get('priority', 'all')
        context['project_filter'] = self.request.GET.get('project', 'all')
        
        return context


class TaskDetailView(LoginRequiredMixin, UserPassesTestMixin, DetailView):
    """View to display task details"""
    model = Task
    template_name = 'projects/task_detail.html'
    context_object_name = 'task'
    
    def test_func(self):
        """Check if user has access to this task"""
        task = self.get_object()
        return (self.request.user == task.project.owner or 
                self.request.user in task.project.members.all() or
                self.request.user == task.assignee)
    
    def get_context_data(self, **kwargs):
        """Add comment form and task history to context"""
        context = super().get_context_data(**kwargs)
        context['comment_form'] = CommentForm()
        context['comments'] = self.object.comments.all()
        context['task_history'] = self.object.history.all()
        context['subtasks'] = self.object.subtasks.all()
        
        # Add update form for task status and hours
        context['update_form'] = TaskUpdateForm(instance=self.object)
        
        return context


class TaskCreateView(LoginRequiredMixin, CreateView):
    """View to create a new task"""
    model = Task
    form_class = TaskForm
    template_name = 'projects/task_form.html'
    
    def get_form_kwargs(self):
        """Pass current user and project_id to form"""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        project_id = self.request.GET.get('project')
        if project_id:
            kwargs['project_id'] = project_id
        return kwargs
    
    def form_valid(self, form):
        """Set created_by to current user"""
        form.instance.created_by = self.request.user
        
        # If no assignee is set, assign to self
        if not form.instance.assignee:
            form.instance.assignee = self.request.user
            
        response = super().form_valid(form)
        logger.info(f"User {self.request.user.username} created task: {form.instance.title}")
        messages.success(self.request, f'Завдання "{form.instance.title}" успішно створено!')
        return response


class TaskUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """View to update task details"""
    model = Task
    form_class = TaskForm
    template_name = 'projects/task_form.html'
    
    def test_func(self):
        """Only project owner, task creator or assignee can update it"""
        task = self.get_object()
        return (self.request.user == task.project.owner or 
                self.request.user == task.created_by or
                self.request.user == task.assignee)
    
    def get_form_kwargs(self):
        """Pass current user to form"""
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        """Track changes to task"""
        old_task = self.get_object()
        response = super().form_valid(form)
        
        # Create task history entries for changes
        tracked_fields = {
            'title': 'Назва',
            'description': 'Опис',
            'status': 'Статус',
            'priority': 'Пріоритет',
            'assignee': 'Виконавець',
            'due_date': 'Термін виконання',
            'estimated_hours': 'Оцінка часу'
        }
        
        for field, field_name in tracked_fields.items():
            old_value = getattr(old_task, field)
            new_value = getattr(form.instance, field)
            
            # Handle special cases like foreign keys
            if field == 'assignee':
                old_value = old_task.assignee.username if old_task.assignee else None
                new_value = form.instance.assignee.username if form.instance.assignee else None
            
            if str(old_value) != str(new_value):
                TaskHistory.objects.create(
                    task=form.instance,
                    user=self.request.user,
                    changed_field=field_name,
                    old_value=str(old_value) if old_value else None,
                    new_value=str(new_value) if new_value else None
                )
        
        logger.info(f"User {self.request.user.username} updated task: {form.instance.title}")
        messages.success(self.request, f'Завдання "{form.instance.title}" успішно оновлено!')
        return response


class TaskDeleteView(LoginRequiredMixin, UserPassesTestMixin, DeleteView):
    """View to delete a task"""
    model = Task
    template_name = 'projects/task_confirm_delete.html'
    
    def test_func(self):
        """Only project owner or task creator can delete it"""
        task = self.get_object()
        return self.request.user == task.project.owner or self.request.user == task.created_by
    
    def get_success_url(self):
        """Redirect to the project detail page after deletion"""
        return reverse('project-detail', kwargs={'pk': self.object.project.pk})
    
    def delete(self, request, *args, **kwargs):
        """Log deletion and show success message"""
        task = self.get_object()
        task_title = task.title
        project_id = task.project.id
        response = super().delete(request, *args, **kwargs)
        logger.info(f"User {self.request.user.username} deleted task: {task_title}")
        messages.success(self.request, f'Завдання "{task_title}" успішно видалено!')
        return response


@login_required
def add_comment(request, task_id):
    """View to add a comment to a task"""
    task = get_object_or_404(Task, id=task_id)
    
    # Check if user has access to this task
    if not (request.user == task.project.owner or 
            request.user in task.project.members.all() or
            request.user == task.assignee):
        messages.error(request, 'У вас немає доступу до цього завдання.')
        return redirect('task-list')
    
    if request.method == 'POST':
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.task = task
            comment.author = request.user
            comment.save()
            logger.info(f"User {request.user.username} added comment to task: {task.title}")
            messages.success(request, 'Коментар успішно додано!')
            return redirect('task-detail', pk=task.id)
    
    # Redirect back to task detail if method is not POST
    return redirect('task-detail', pk=task.id)


@login_required
def update_task_status(request, task_id):
    """View to quickly update task status and log hours"""
    task = get_object_or_404(Task, id=task_id)
    
    # Check if user has access to update this task
    if not (request.user == task.project.owner or 
            request.user == task.created_by or
            request.user == task.assignee):
        messages.error(request, 'У вас немає доступу до оновлення цього завдання.')
        return redirect('task-detail', pk=task.id)
    
    if request.method == 'POST':
        form = TaskUpdateForm(request.POST, instance=task)
        if form.is_valid():
            old_status = task.status
            old_actual_hours = task.actual_hours
            
            updated_task = form.save()
            
            # Create task history for status change
            if old_status != updated_task.status:
                TaskHistory.objects.create(
                    task=updated_task,
                    user=request.user,
                    changed_field='Статус',
                    old_value=dict(Task.STATUS_CHOICES).get(old_status),
                    new_value=dict(Task.STATUS_CHOICES).get(updated_task.status)
                )
            
            # Create task history for hours change
            if old_actual_hours != updated_task.actual_hours and updated_task.actual_hours is not None:
                TaskHistory.objects.create(
                    task=updated_task,
                    user=request.user,
                    changed_field='Фактичний час',
                    old_value=str(old_actual_hours) if old_actual_hours else '0',
                    new_value=str(updated_task.actual_hours)
                )
            
            logger.info(f"User {request.user.username} updated status of task: {task.title}")
            messages.success(request, f'Статус завдання успішно оновлено!')
    else:
        messages.error(request, 'Невірний метод запиту.')
    
    return redirect('task-detail', pk=task.id)
