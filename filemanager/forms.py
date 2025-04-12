from django import forms
from django.db.models import Q
from .models import File
from projects.models import Project, Task


class FileUploadForm(forms.ModelForm):
    """Form for uploading files"""
    class Meta:
        model = File
        fields = ['file', 'project', 'task']
        widgets = {
            'file': forms.FileInput(attrs={'class': 'form-control'}),
            'project': forms.Select(attrs={'class': 'form-select'}),
            'task': forms.Select(attrs={'class': 'form-select'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            # Filter projects by user's access
            self.fields['project'].queryset = Project.objects.filter(
                Q(owner=self.user) | Q(members=self.user)
            ).order_by('title')
            
            # Initially disable the task field
            self.fields['task'].queryset = Task.objects.none()
            
            # If project is already selected, filter tasks by project
            if 'project' in self.initial:
                project = self.initial['project']
                if project:
                    self.fields['task'].queryset = Task.objects.filter(project=project).order_by('title')
        
        # Add help texts
        self.fields['project'].help_text = 'Оберіть проект, до якого відноситься файл.'
        self.fields['task'].help_text = 'Оберіть завдання, до якого відноситься файл (необов\'язково).'
        
        # Update labels
        self.fields['file'].label = 'Виберіть файл'
        self.fields['project'].label = 'Проект'
        self.fields['task'].label = 'Завдання'
    
    def clean(self):
        cleaned_data = super().clean()
        project = cleaned_data.get('project')
        task = cleaned_data.get('task')
        
        # Check if task belongs to selected project
        if task and project and task.project != project:
            self.add_error('task', 'Це завдання не належить до вибраного проекту.')
        
        return cleaned_data
