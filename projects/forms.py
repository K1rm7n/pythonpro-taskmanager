from django import forms
from .models import Project, Task, Comment


class ProjectForm(forms.ModelForm):
    """Form for creating and updating projects"""
    class Meta:
        model = Project
        fields = ['title', 'description', 'status', 'start_date', 'end_date', 'members']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'start_date': forms.DateInput(attrs={'type': 'date'}),
            'end_date': forms.DateInput(attrs={'type': 'date'}),
            'members': forms.SelectMultiple(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        if self.user:
            # Exclude current user from members field as they're already the owner
            self.fields['members'].queryset = self.fields['members'].queryset.exclude(id=self.user.id)


class TaskForm(forms.ModelForm):
    """Form for creating and updating tasks"""
    class Meta:
        model = Task
        fields = [
            'title', 'description', 'project', 'assignee', 
            'status', 'priority', 'due_date', 'parent_task',
            'estimated_hours'
        ]
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'project': forms.Select(attrs={'class': 'form-select'}),
            'assignee': forms.Select(attrs={'class': 'form-select'}),
            'parent_task': forms.Select(attrs={'class': 'form-select'}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        project_id = kwargs.pop('project_id', None)
        super().__init__(*args, **kwargs)
        
        if self.user:
            # Filter projects by user's projects and owned projects
            projects = Project.objects.filter(
                models.Q(members=self.user) | models.Q(owner=self.user)
            ).distinct()
            self.fields['project'].queryset = projects
            
            # For existing task being edited
            if self.instance and self.instance.pk:
                # Filter parent tasks to exclude itself and its descendants
                task_descendants = Task.objects.filter(parent_task=self.instance)
                self.fields['parent_task'].queryset = Task.objects.filter(
                    project=self.instance.project
                ).exclude(
                    models.Q(pk=self.instance.pk) | models.Q(pk__in=task_descendants)
                )
            
            # For new task or when project is preselected
            elif project_id:
                self.fields['project'].initial = project_id
                self.fields['project'].widget.attrs['readonly'] = True
                self.fields['parent_task'].queryset = Task.objects.filter(project_id=project_id)


class TaskUpdateForm(forms.ModelForm):
    """Form for updating task status and logging hours"""
    actual_hours = forms.DecimalField(
        max_digits=5, decimal_places=2, required=False,
        label='Затрачений час (годин)', help_text='Вкажіть скільки годин ви витратили на це завдання'
    )
    
    class Meta:
        model = Task
        fields = ['status', 'actual_hours']


class CommentForm(forms.ModelForm):
    """Form for adding comments to tasks"""
    class Meta:
        model = Comment
        fields = ['text']
        widgets = {
            'text': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Додайте коментар...'}),
        }
        labels = {
            'text': '',
        }
