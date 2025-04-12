from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.db.models import Count, Sum, Q, F, ExpressionWrapper, fields, Avg
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth
from django.utils import timezone
from datetime import timedelta
import json

from projects.models import Project, Task, Comment
from .models import ProjectStatistics, UserActivity


@login_required
def project_analytics_view(request):
    """View for project analytics"""
    # Get user's projects
    user_projects = Project.objects.filter(
        Q(owner=request.user) | Q(members=request.user)
    ).distinct()
    
    # Get selected project or use the first one
    project_id = request.GET.get('project')
    if project_id and project_id.isdigit():
        project = get_object_or_404(Project, id=project_id)
        if not (project.owner == request.user or request.user in project.members.all()):
            # Fallback to first project if user doesn't have access to selected one
            project = user_projects.first()
    else:
        project = user_projects.first()
    
    context = {
        'projects': user_projects,
        'selected_project': project,
    }
    
    if project:
        # Task status distribution
        task_status_counts = Task.objects.filter(project=project).values('status').annotate(
            count=Count('id')
        ).order_by('status')
        
        status_labels = []
        status_data = []
        status_colors = []
        
        status_color_map = {
            'todo': '#6c757d',  # secondary
            'in_progress': '#0d6efd',  # primary
            'review': '#ffc107',  # warning
            'completed': '#198754',  # success
        }
        
        for item in task_status_counts:
            status = item['status']
            status_labels.append(dict(Task.STATUS_CHOICES)[status])
            status_data.append(item['count'])
            status_colors.append(status_color_map.get(status, '#6c757d'))
        
        context['task_status_labels'] = json.dumps(status_labels)
        context['task_status_data'] = json.dumps(status_data)
        context['task_status_colors'] = json.dumps(status_colors)
        
        # Task priority distribution
        task_priority_counts = Task.objects.filter(project=project).values('priority').annotate(
            count=Count('id')
        ).order_by('priority')
        
        priority_labels = []
        priority_data = []
        priority_colors = []
        
        priority_color_map = {
            'low': '#198754',  # success
            'medium': '#0dcaf0',  # info
            'high': '#ffc107',  # warning
            'urgent': '#dc3545',  # danger
        }
        
        for item in task_priority_counts:
            priority = item['priority']
            priority_labels.append(dict(Task.PRIORITY_CHOICES)[priority])
            priority_data.append(item['count'])
            priority_colors.append(priority_color_map.get(priority, '#6c757d'))
        
        context['task_priority_labels'] = json.dumps(priority_labels)
        context['task_priority_data'] = json.dumps(priority_data)
        context['task_priority_colors'] = json.dumps(priority_colors)
        
        # Task completion over time
        thirty_days_ago = timezone.now().date() - timedelta(days=30)
        
        task_completion_data = Task.objects.filter(
            project=project, 
            status='completed',
            updated_at__date__gte=thirty_days_ago
        ).annotate(
            day=TruncDay('updated_at')
        ).values('day').annotate(
            count=Count('id')
        ).order_by('day')
        
        completion_dates = []
        completion_counts = []
        
        # Fill in missing dates with zero values
        date_dict = {}
        current_date = thirty_days_ago
        end_date = timezone.now().date()
        while current_date <= end_date:
            date_dict[current_date.strftime('%Y-%m-%d')] = 0
            current_date += timedelta(days=1)
        
        for item in task_completion_data:
            date_str = item['day'].strftime('%Y-%m-%d')
            date_dict[date_str] = item['count']
        
        for date_str, count in date_dict.items():
            completion_dates.append(date_str)
            completion_counts.append(count)
        
        context['completion_dates'] = json.dumps(completion_dates)
        context['completion_counts'] = json.dumps(completion_counts)
        
        # User contribution data
        user_contributions = Task.objects.filter(
            project=project, status='completed'
        ).values('assignee__username', 'assignee__first_name', 'assignee__last_name').annotate(
            completed_count=Count('id')
        ).order_by('-completed_count')
        
        contribution_labels = []
        contribution_data = []
        contribution_colors = []
        
        # Generate colors for each user
        color_palette = ['#0d6efd', '#6610f2', '#6f42c1', '#d63384', '#dc3545', '#fd7e14', '#ffc107', '#198754', '#20c997', '#0dcaf0']
        
        for idx, item in enumerate(user_contributions):
            if item['assignee__first_name'] and item['assignee__last_name']:
                name = f"{item['assignee__first_name']} {item['assignee__last_name']}"
            else:
                name = item['assignee__username']
                
            contribution_labels.append(name)
            contribution_data.append(item['completed_count'])
            contribution_colors.append(color_palette[idx % len(color_palette)])
        
        context['contribution_labels'] = json.dumps(contribution_labels)
        context['contribution_data'] = json.dumps(contribution_data)
        context['contribution_colors'] = json.dumps(contribution_colors)
        
        # Task statistics
        context['total_tasks'] = Task.objects.filter(project=project).count()
        context['completed_tasks'] = Task.objects.filter(project=project, status='completed').count()
        context['overdue_tasks'] = Task.objects.filter(
            project=project,
            due_date__lt=timezone.now().date(),
            status__in=['todo', 'in_progress', 'review']
        ).count()
        
        # Calculate average completion time
        completed_tasks = Task.objects.filter(
            project=project,
            status='completed'
        )
        
        total_time = timedelta()
        counted_tasks = 0
        
        for task in completed_tasks:
            # Find the last status change to 'completed' in the history
            completion_history = task.history.filter(changed_field='Статус', new_value='Завершено').order_by('-timestamp').first()
            
            if completion_history and task.created_at:
                completion_time = completion_history.timestamp - task.created_at
                if completion_time.total_seconds() > 0:  # Ensure positive time
                    total_time += completion_time
                    counted_tasks += 1
        
        if counted_tasks > 0:
            avg_completion_seconds = total_time.total_seconds() / counted_tasks
            avg_days = int(avg_completion_seconds // (24 * 3600))
            avg_hours = int((avg_completion_seconds % (24 * 3600)) // 3600)
            
            context['avg_completion_time'] = f"{avg_days} днів, {avg_hours} годин"
        else:
            context['avg_completion_time'] = "Н/Д"
        
    return render(request, 'analytics/project_analytics.html', context)


@login_required
def team_analytics_view(request):
    """View for team analytics"""
    # Get user's projects for filtering
    user_projects = Project.objects.filter(
        Q(owner=request.user) | Q(members=request.user)
    ).distinct()
    
    # Get selected project or use all user's projects
    project_id = request.GET.get('project')
    if project_id and project_id != 'all' and project_id.isdigit():
        projects = [get_object_or_404(Project, id=project_id)]
        if not (projects[0].owner == request.user or request.user in projects[0].members.all()):
            # Fallback to all projects if user doesn't have access to selected one
            projects = user_projects
    else:
        projects = user_projects
    
    # Get time range filter
    time_range = request.GET.get('time_range', '30')  # Default to 30 days
    days = int(time_range)
    start_date = timezone.now().date() - timedelta(days=days)
    
    project_ids = [p.id for p in projects]
    
    context = {
        'projects': user_projects,
        'selected_project_id': project_id if project_id else 'all',
        'time_range': time_range,
    }
    
    # Get team members
    team_members = set()
    for project in projects:
        team_members.add(project.owner)
        for member in project.members.all():
            team_members.add(member)
    
    # User productivity data
    user_productivity = []
    
    for user in team_members:
        user_data = {
            'username': user.username,
            'name': user.get_full_name() or user.username,
            'tasks_created': Task.objects.filter(
                created_by=user, 
                project_id__in=project_ids,
                created_at__date__gte=start_date
            ).count(),
            'tasks_completed': Task.objects.filter(
                assignee=user, 
                status='completed',
                project_id__in=project_ids,
                updated_at__date__gte=start_date
            ).count(),
            'comments': Comment.objects.filter(
                author=user,
                task__project_id__in=project_ids,
                created_at__date__gte=start_date
            ).count(),
            'hours_logged': Task.objects.filter(
                assignee=user,
                project_id__in=project_ids,
                actual_hours__isnull=False
            ).aggregate(total=Sum('actual_hours'))['total'] or 0,
        }
        
        user_productivity.append(user_data)
    
    # Sort by tasks completed (most productive first)
    user_productivity.sort(key=lambda x: x['tasks_completed'], reverse=True)
    context['user_productivity'] = user_productivity
    
    # Task completion trend over time
    if time_range == '365':
        # For year view, group by month
        trunc_function = TruncMonth
        date_format = '%Y-%m'
    elif time_range == '90':
        # For 90-day view, group by week
        trunc_function = TruncWeek
        date_format = '%Y-%m-%d'
    else:
        # For 30-day or 7-day view, group by day
        trunc_function = TruncDay
        date_format = '%Y-%m-%d'
    
    completion_trend = Task.objects.filter(
        status='completed',
        project_id__in=project_ids,
        updated_at__date__gte=start_date
    ).annotate(
        date=trunc_function('updated_at')
    ).values('date').annotate(
        count=Count('id')
    ).order_by('date')
    
    # Fill in missing dates with zero values
    trend_dates = []
    trend_counts = []
    
    # Initialize date dictionary with all dates in range
    date_dict = {}
    current_date = start_date
    end_date = timezone.now().date()
    
    if time_range == '365':
        # For year view, create month buckets
        while current_date <= end_date:
            month_key = current_date.strftime(date_format)
            if month_key not in date_dict:
                date_dict[month_key] = 0
            current_date += timedelta(days=1)
    elif time_range == '90':
        # For 90-day view, create week buckets
        while current_date <= end_date:
            # Use the first day of the week as key
            week_start = current_date - timedelta(days=current_date.weekday())
            week_key = week_start.strftime(date_format)
            if week_key not in date_dict:
                date_dict[week_key] = 0
            current_date += timedelta(days=1)
    else:
        # For 30-day or 7-day view, create daily buckets
        while current_date <= end_date:
            date_dict[current_date.strftime(date_format)] = 0
            current_date += timedelta(days=1)
    
    # Fill in actual counts
    for item in completion_trend:
        date_str = item['date'].strftime(date_format)
        date_dict[date_str] = item['count']
    
    # Convert dictionary to lists for chart
    for date_str, count in sorted(date_dict.items()):
        trend_dates.append(date_str)
        trend_counts.append(count)
    
    context['trend_dates'] = json.dumps(trend_dates)
    context['trend_counts'] = json.dumps(trend_counts)
    
    # Workload distribution: tasks per user
    workload_data = Task.objects.filter(
        project_id__in=project_ids,
        status__in=['todo', 'in_progress', 'review']
    ).values('assignee__username', 'assignee__first_name', 'assignee__last_name').annotate(
        count=Count('id')
    ).order_by('-count')
    
    workload_labels = []
    workload_counts = []
    
    for item in workload_data:
        if item['assignee__username']:  # Skip unassigned tasks
            if item['assignee__first_name'] and item['assignee__last_name']:
                name = f"{item['assignee__first_name']} {item['assignee__last_name']}"
            else:
                name = item['assignee__username']
                
            workload_labels.append(name)
            workload_counts.append(item['count'])
    
    context['workload_labels'] = json.dumps(workload_labels)
    context['workload_counts'] = json.dumps(workload_counts)
    
    # Team efficiency data
    total_completed = Task.objects.filter(
        project_id__in=project_ids,
        status='completed',
        updated_at__date__gte=start_date
    ).count()
    
    total_created = Task.objects.filter(
        project_id__in=project_ids,
        created_at__date__gte=start_date
    ).count()
    
    context['total_completed'] = total_completed
    context['total_created'] = total_created
    
    if total_created > 0:
        context['completion_rate'] = round((total_completed / total_created) * 100)
    else:
        context['completion_rate'] = 0
    
    # Overdue tasks count
    context['overdue_tasks'] = Task.objects.filter(
        project_id__in=project_ids,
        due_date__lt=timezone.now().date(),
        status__in=['todo', 'in_progress', 'review']
    ).count()
    
    return render(request, 'analytics/team_analytics.html', context)
