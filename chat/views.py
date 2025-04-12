from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Max, Count, F, Exists, OuterRef
from django.http import JsonResponse
from django.utils import timezone
from django.db import transaction
from django.contrib import messages

from projects.models import Project
from .models import ChatRoom, Message, UserChatStatus


@login_required
def chat_room_view(request, room_id=None):
    """View for displaying the chat interface"""
    # Get all chat rooms the user has access to
    user_project_ids = Project.objects.filter(
        Q(owner=request.user) | Q(members=request.user)
    ).values_list('id', flat=True)
    
    # Get project chat rooms
    project_chat_rooms = ChatRoom.objects.filter(
        is_project_room=True, 
        project_id__in=user_project_ids
    ).select_related('project')
    
    # Get other chat rooms the user has participated in
    other_chat_rooms = ChatRoom.objects.filter(
        is_project_room=False,
        messages__sender=request.user
    ).distinct()
    
    # Combine all accessible chat rooms
    all_chat_rooms = list(project_chat_rooms) + list(other_chat_rooms)
    
    # Add unread messages count to each room
    for room in all_chat_rooms:
        # Get or create user chat status for this room
        chat_status, created = UserChatStatus.objects.get_or_create(
            user=request.user,
            room=room
        )
        
        # Add unread count to the room object
        room.unread_count = chat_status.unread_count()
    
    # If a specific room is requested, check if user has access
    current_room = None
    if room_id:
        current_room = get_object_or_404(ChatRoom, id=room_id)
        
        # Check if user has access to this room
        if current_room.is_project_room:
            # For project rooms, check if user is owner or member
            project = current_room.project
            if not (project.owner == request.user or request.user in project.members.all()):
                messages.error(request, 'У вас немає доступу до цієї кімнати чату.')
                return redirect('chat-room')
        else:
            # For other rooms, check if user has participated
            if not Message.objects.filter(room=current_room, sender=request.user).exists():
                messages.error(request, 'У вас немає доступу до цієї кімнати чату.')
                return redirect('chat-room')
        
        # Update user chat status for this room
        with transaction.atomic():
            chat_status, created = UserChatStatus.objects.get_or_create(
                user=request.user,
                room=current_room
            )
            chat_status.last_visited = timezone.now()
            chat_status.save()
    
    # If no room is specified or accessible, use the first available room
    elif all_chat_rooms:
        return redirect('chat-room', room_id=all_chat_rooms[0].id)
    
    # Get participants for the current room
    participants = []
    if current_room:
        participants = current_room.get_participants()
    
    context = {
        'rooms': all_chat_rooms,
        'current_room': current_room,
        'participants': participants,
    }
    
    return render(request, 'chat/chat_room.html', context)


@login_required
def create_project_chat(request, project_id):
    """Create a chat room for a project if it doesn't exist"""
    # Check if the user has access to the project
    project = get_object_or_404(
        Project,
        id=project_id,
        Q(owner=request.user) | Q(members=request.user)
    )
    
    # Create chat room if it doesn't exist
    chat_room, created = ChatRoom.objects.get_or_create(
        project=project,
        is_project_room=True,
        defaults={'name': f"Чат проекту: {project.title}"}
    )
    
    return redirect('chat-room', room_id=chat_room.id)


@login_required
def create_custom_chat(request):
    """Create a custom chat room"""
    if request.method == 'POST':
        name = request.POST.get('name', '').strip()
        
        if name:
            # Create a new custom chat room
            chat_room = ChatRoom.objects.create(
                name=name,
                is_project_room=False
            )
            
            # Add an initial system message
            Message.objects.create(
                room=chat_room,
                sender=request.user,
                content=f"Чат-кімната '{name}' створена користувачем {request.user.get_full_name() or request.user.username}",
                is_read=True
            )
            
            return redirect('chat-room', room_id=chat_room.id)
        else:
            messages.error(request, 'Будь ласка, вкажіть назву кімнати чату.')
    
    return redirect('chat-room')
