from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404, JsonResponse
from django.db.models import Q
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.utils import timezone

from .models import File, FileAccess
from .forms import FileUploadForm
from projects.models import Project, Task

import mimetypes
import os


@login_required
def file_list_view(request):
    """View to display list of files with filtering options"""
    # Get all projects the user has access to
    user_projects = Project.objects.filter(
        Q(owner=request.user) | Q(members=request.user)
    ).values_list('id', flat=True)
    
    # Get all files the user has access to
    files = File.objects.filter(
        Q(project_id__in=user_projects) |
        Q(task__project_id__in=user_projects) |
        Q(uploaded_by=request.user)
    ).select_related('project', 'task', 'uploaded_by').order_by('-uploaded_at')
    
    # Apply filters if provided
    project_filter = request.GET.get('project')
    task_filter = request.GET.get('task')
    type_filter = request.GET.get('type')
    
    if project_filter and project_filter.isdigit():
        files = files.filter(Q(project_id=project_filter) | Q(task__project_id=project_filter))
    
    if task_filter and task_filter.isdigit():
        files = files.filter(task_id=task_filter)
    
    if type_filter:
        if type_filter == 'image':
            files = files.filter(content_type__startswith='image/')
        elif type_filter == 'document':
            files = files.filter(
                Q(content_type__contains='pdf') |
                Q(content_type__contains='word') |
                Q(content_type__contains='excel') |
                Q(content_type__contains='powerpoint') |
                Q(content_type__contains='text')
            )
        elif type_filter == 'archive':
            files = files.filter(
                Q(content_type__contains='zip') |
                Q(content_type__contains='rar') |
                Q(content_type__contains='tar') |
                Q(content_type__contains='gzip')
            )
        elif type_filter == 'other':
            files = files.exclude(
                Q(content_type__startswith='image/') |
                Q(content_type__contains='pdf') |
                Q(content_type__contains='word') |
                Q(content_type__contains='excel') |
                Q(content_type__contains='powerpoint') |
                Q(content_type__contains='text') |
                Q(content_type__contains='zip') |
                Q(content_type__contains='rar') |
                Q(content_type__contains='tar') |
                Q(content_type__contains='gzip')
            )
    
    # Get all projects for filter dropdown
    projects = Project.objects.filter(
        Q(owner=request.user) | Q(members=request.user)
    ).order_by('title')
    
    # Get selected project's tasks for filter dropdown
    tasks = []
    if project_filter and project_filter.isdigit():
        tasks = Task.objects.filter(project_id=project_filter).order_by('title')
    
    context = {
        'files': files,
        'projects': projects,
        'tasks': tasks,
        'project_filter': project_filter,
        'task_filter': task_filter,
        'type_filter': type_filter,
    }
    
    return render(request, 'filemanager/file_list.html', context)


@login_required
def file_upload_view(request):
    """View to upload new files"""
    if request.method == 'POST':
        form = FileUploadForm(request.POST, request.FILES, user=request.user)
        
        if form.is_valid():
            # Process the uploaded file
            uploaded_file = request.FILES['file']
            
            # Create file object
            file_obj = form.save(commit=False)
            file_obj.name = uploaded_file.name
            file_obj.size = uploaded_file.size
            file_obj.content_type = uploaded_file.content_type or mimetypes.guess_type(uploaded_file.name)[0] or 'application/octet-stream'
            file_obj.uploaded_by = request.user
            file_obj.save()
            
            messages.success(request, f'Файл "{file_obj.name}" успішно завантажено.')
            
            # Redirect to appropriate page based on where the upload was initiated
            if request.GET.get('task'):
                return redirect('task-detail', pk=request.GET.get('task'))
            elif request.GET.get('project'):
                return redirect('project-detail', pk=request.GET.get('project'))
            else:
                return redirect('file-list')
    else:
        # Initialize form with pre-selected project or task
        initial_data = {}
        
        task_id = request.GET.get('task')
        project_id = request.GET.get('project')
        
        if task_id and task_id.isdigit():
            try:
                task = Task.objects.select_related('project').get(
                    id=task_id,
                    Q(project__owner=request.user) | Q(project__members=request.user) | Q(assignee=request.user)
                )
                initial_data['task'] = task
                initial_data['project'] = task.project
            except Task.DoesNotExist:
                pass
                
        elif project_id and project_id.isdigit():
            try:
                project = Project.objects.get(
                    id=project_id,
                    Q(owner=request.user) | Q(members=request.user)
                )
                initial_data['project'] = project
            except Project.DoesNotExist:
                pass
        
        form = FileUploadForm(initial=initial_data, user=request.user)
    
    context = {
        'form': form,
        'task_id': request.GET.get('task'),
        'project_id': request.GET.get('project'),
    }
    
    return render(request, 'filemanager/file_upload.html', context)


@login_required
def file_download_view(request, file_id):
    """View to download a file"""
    # Get the file object and check access permissions
    file_obj = get_object_or_404(
        File.objects.select_related('project', 'task'),
        id=file_id
    )
    
    # Check if user has access to this file
    has_access = False
    
    # Check if user uploaded the file
    if file_obj.uploaded_by == request.user:
        has_access = True
    
    # Check if user has access to the project or task
    elif file_obj.project:
        has_access = (file_obj.project.owner == request.user or request.user in file_obj.project.members.all())
    
    elif file_obj.task:
        project = file_obj.task.project
        has_access = (project.owner == request.user or 
                     request.user in project.members.all() or 
                     file_obj.task.assignee == request.user)
    
    if not has_access:
        raise Http404("У вас немає доступу до цього файлу.")
    
    # Log file access
    FileAccess.objects.create(
        file=file_obj,
        user=request.user
    )
    
    # Serve the file
    file_path = file_obj.file.path
    
    if os.path.exists(file_path):
        with open(file_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type=file_obj.content_type)
            response['Content-Disposition'] = f'attachment; filename="{file_obj.name}"'
            return response
    else:
        raise Http404("Файл не знайдено.")


@login_required
@require_POST
def file_delete_view(request, file_id):
    """View to delete a file"""
    # Get the file object
    file_obj = get_object_or_404(File, id=file_id)
    
    # Check if user has permission to delete this file
    if file_obj.uploaded_by != request.user and (
        not file_obj.project or file_obj.project.owner != request.user
    ) and (
        not file_obj.task or file_obj.task.project.owner != request.user
    ):
        messages.error(request, "У вас немає дозволу на видалення цього файлу.")
        return redirect('file-list')
    
    # Store file name for success message
    file_name = file_obj.name
    
    # Delete the file
    file_obj.delete()
    
    messages.success(request, f'Файл "{file_name}" успішно видалено.')
    
    # Return to the appropriate page
    referer = request.META.get('HTTP_REFERER')
    if referer:
        return redirect(referer)
    else:
        return redirect('file-list')


@login_required
def get_task_options(request):
    """AJAX view to get tasks for a selected project"""
    project_id = request.GET.get('project_id')
    
    if not project_id or not project_id.isdigit():
        return JsonResponse({'tasks': []})
    
    # Check if user has access to this project
    try:
        project = Project.objects.get(
            id=project_id,
            Q(owner=request.user) | Q(members=request.user)
        )
    except Project.DoesNotExist:
        return JsonResponse({'tasks': []})
    
    # Get tasks for this project
    tasks = Task.objects.filter(project=project).values('id', 'title')
    
    return JsonResponse({'tasks': list(tasks)})
