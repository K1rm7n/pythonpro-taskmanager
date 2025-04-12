from django.db import models
from django.contrib.auth.models import User
from projects.models import Project, Task
from django.utils import timezone


class ProjectStatistics(models.Model):
    """Model to store project statistics snapshots"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='statistics')
    date = models.DateField(default=timezone.now)
    total_tasks = models.PositiveIntegerField(default=0)
    completed_tasks = models.PositiveIntegerField(default=0)
    todo_tasks = models.PositiveIntegerField(default=0)
    in_progress_tasks = models.PositiveIntegerField(default=0)
    review_tasks = models.PositiveIntegerField(default=0)
    overdue_tasks = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        return f"Статистика проекту {self.project.title} за {self.date}"
    
    class Meta:
        verbose_name = 'Статистика проекту'
        verbose_name_plural = 'Статистика проектів'
        ordering = ['-date']
        unique_together = ['project', 'date']


class UserActivity(models.Model):
    """Model to track user activity for analytics"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='activities')
    date = models.DateField(default=timezone.now)
    tasks_created = models.PositiveIntegerField(default=0)
    tasks_completed = models.PositiveIntegerField(default=0)
    comments_added = models.PositiveIntegerField(default=0)
    hours_logged = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    
    def __str__(self):
        return f"Активність користувача {self.user.username} за {self.date}"
    
    class Meta:
        verbose_name = 'Активність користувача'
        verbose_name_plural = 'Активність користувачів'
        ordering = ['-date']
        unique_together = ['user', 'date']
