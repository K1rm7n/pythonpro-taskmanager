from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone


class Project(models.Model):
    """Project model to organize tasks"""
    
    STATUS_CHOICES = [
        ('planning', 'Планування'),
        ('in_progress', 'В процесі'),
        ('on_hold', 'На паузі'),
        ('completed', 'Завершено'),
        ('cancelled', 'Скасовано'),
    ]
    
    title = models.CharField(max_length=100, verbose_name='Назва')
    description = models.TextField(verbose_name='Опис')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='planning', verbose_name='Статус')
    start_date = models.DateField(verbose_name='Дата початку')
    end_date = models.DateField(null=True, blank=True, verbose_name='Дата завершення')
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='owned_projects', verbose_name='Власник')
    members = models.ManyToManyField(User, related_name='projects', blank=True, verbose_name='Учасники')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата створення')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата оновлення')
    
    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('project-detail', kwargs={'pk': self.pk})
    
    def get_progress(self):
        """Calculate project progress based on completed tasks"""
        tasks = self.tasks.all()
        if not tasks:
            return 0
        completed_tasks = tasks.filter(status='completed').count()
        return int((completed_tasks / tasks.count()) * 100)
    
    def is_overdue(self):
        """Check if project is overdue"""
        if self.end_date and self.status != 'completed':
            return self.end_date < timezone.now().date()
        return False
    
    class Meta:
        verbose_name = 'Проект'
        verbose_name_plural = 'Проекти'
        ordering = ['-created_at']


class Task(models.Model):
    """Task model for project management"""
    
    PRIORITY_CHOICES = [
        ('low', 'Низький'),
        ('medium', 'Середній'),
        ('high', 'Високий'),
        ('urgent', 'Терміново'),
    ]
    
    STATUS_CHOICES = [
        ('todo', 'Зробити'),
        ('in_progress', 'В процесі'),
        ('review', 'На перевірці'),
        ('completed', 'Завершено'),
    ]
    
    title = models.CharField(max_length=100, verbose_name='Назва')
    description = models.TextField(verbose_name='Опис')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tasks', verbose_name='Проект')
    assignee = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, 
        related_name='assigned_tasks', verbose_name='Виконавець'
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='todo', verbose_name='Статус')
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default='medium', verbose_name='Пріоритет')
    due_date = models.DateField(null=True, blank=True, verbose_name='Термін виконання')
    created_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='created_tasks', verbose_name='Створив'
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата створення')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата оновлення')
    parent_task = models.ForeignKey(
        'self', on_delete=models.CASCADE, null=True, blank=True, 
        related_name='subtasks', verbose_name='Батьківське завдання'
    )
    estimated_hours = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True, 
        verbose_name='Оцінка часу (годин)'
    )
    actual_hours = models.DecimalField(
        max_digits=5, decimal_places=2, null=True, blank=True, 
        verbose_name='Фактичний час (годин)'
    )
    
    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('task-detail', kwargs={'pk': self.pk})
    
    def is_overdue(self):
        """Check if task is overdue"""
        if self.due_date and self.status != 'completed':
            return self.due_date < timezone.now().date()
        return False
    
    class Meta:
        verbose_name = 'Завдання'
        verbose_name_plural = 'Завдання'
        ordering = ['-created_at']


class Comment(models.Model):
    """Comment model for tasks"""
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments', verbose_name='Завдання')
    author = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Автор')
    text = models.TextField(verbose_name='Текст')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата створення')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата оновлення')
    
    def __str__(self):
        return f'Коментар від {self.author.username} до завдання {self.task.title}'
    
    class Meta:
        verbose_name = 'Коментар'
        verbose_name_plural = 'Коментарі'
        ordering = ['created_at']


class TaskHistory(models.Model):
    """Model to track task history changes"""
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='history', verbose_name='Завдання')
    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name='Користувач')
    changed_field = models.CharField(max_length=50, verbose_name='Змінене поле')
    old_value = models.TextField(null=True, blank=True, verbose_name='Старе значення')
    new_value = models.TextField(null=True, blank=True, verbose_name='Нове значення')
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='Час зміни')
    
    def __str__(self):
        return f'Зміна {self.changed_field} в завданні {self.task.title}'
    
    class Meta:
        verbose_name = 'Історія завдання'
        verbose_name_plural = 'Історія завдань'
        ordering = ['-timestamp']
