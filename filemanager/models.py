from django.db import models
from django.contrib.auth.models import User
from projects.models import Project, Task
import os
import uuid


def get_file_path(instance, filename):
    """Generate a unique filename for uploaded files"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    
    # Path format: files/project_id/task_id/filename
    if instance.task:
        return os.path.join('files', str(instance.task.project.id), str(instance.task.id), filename)
    elif instance.project:
        return os.path.join('files', str(instance.project.id), filename)
    else:
        return os.path.join('files', 'general', filename)


class File(models.Model):
    """Model for storing file uploads"""
    name = models.CharField(max_length=255, verbose_name='Назва')
    file = models.FileField(upload_to=get_file_path, verbose_name='Файл')
    size = models.PositiveIntegerField(verbose_name='Розмір (байти)')
    content_type = models.CharField(max_length=100, verbose_name='Тип вмісту')
    
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name='files',
        null=True, blank=True, verbose_name='Проект'
    )
    task = models.ForeignKey(
        Task, on_delete=models.CASCADE, related_name='files',
        null=True, blank=True, verbose_name='Завдання'
    )
    
    uploaded_by = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='uploaded_files',
        verbose_name='Завантажив'
    )
    uploaded_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата завантаження')
    
    def __str__(self):
        return self.name
    
    def get_extension(self):
        """Get file extension"""
        return self.name.split('.')[-1].lower() if '.' in self.name else ''
    
    def get_icon_class(self):
        """Get Font Awesome icon class based on file type"""
        ext = self.get_extension()
        
        # Images
        if ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp', 'svg', 'webp']:
            return 'fas fa-file-image'
        
        # Documents
        elif ext in ['pdf']:
            return 'fas fa-file-pdf'
        elif ext in ['doc', 'docx']:
            return 'fas fa-file-word'
        elif ext in ['xls', 'xlsx', 'csv']:
            return 'fas fa-file-excel'
        elif ext in ['ppt', 'pptx']:
            return 'fas fa-file-powerpoint'
        elif ext in ['txt', 'md', 'rtf']:
            return 'fas fa-file-alt'
        
        # Archives
        elif ext in ['zip', 'rar', '7z', 'tar', 'gz']:
            return 'fas fa-file-archive'
        
        # Code
        elif ext in ['html', 'css', 'js', 'py', 'java', 'cpp', 'c', 'php']:
            return 'fas fa-file-code'
        
        # Audio
        elif ext in ['mp3', 'wav', 'ogg', 'flac']:
            return 'fas fa-file-audio'
        
        # Video
        elif ext in ['mp4', 'avi', 'mov', 'wmv', 'mkv']:
            return 'fas fa-file-video'
        
        # Default
        else:
            return 'fas fa-file'
    
    def delete(self, *args, **kwargs):
        """Delete file from storage when model is deleted"""
        # Delete the file from storage
        if self.file:
            # Check if the file exists
            if os.path.isfile(self.file.path):
                os.remove(self.file.path)
        
        # Call the parent delete method
        super().delete(*args, **kwargs)
    
    class Meta:
        verbose_name = 'Файл'
        verbose_name_plural = 'Файли'
        ordering = ['-uploaded_at']


class FileAccess(models.Model):
    """Model to track file access history"""
    file = models.ForeignKey(File, on_delete=models.CASCADE, related_name='accesses', verbose_name='Файл')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='file_accesses', verbose_name='Користувач')
    accessed_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата доступу')
    
    def __str__(self):
        return f"{self.user.username} доступ до {self.file.name} о {self.accessed_at}"
    
    class Meta:
        verbose_name = 'Доступ до файлу'
        verbose_name_plural = 'Доступи до файлів'
        ordering = ['-accessed_at']
