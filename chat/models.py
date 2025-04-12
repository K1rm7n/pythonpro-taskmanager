from django.db import models
from django.contrib.auth.models import User
from projects.models import Project


class ChatRoom(models.Model):
    """Model for chat rooms"""
    name = models.CharField(max_length=100, verbose_name='Назва')
    project = models.OneToOneField(
        Project, on_delete=models.CASCADE, related_name='chat_room', null=True, blank=True,
        verbose_name='Проект'
    )
    is_project_room = models.BooleanField(default=True, verbose_name='Кімната проекту')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Створено')
    
    def __str__(self):
        if self.is_project_room and self.project:
            return f"Чат проекту: {self.project.title}"
        else:
            return self.name
    
    def get_participants(self):
        """Get all participants in this chat room"""
        if self.is_project_room and self.project:
            # For project rooms, include project owner and members
            participants = list(self.project.members.all())
            participants.append(self.project.owner)
            return participants
        else:
            # For custom chat rooms, get all users from chat messages
            message_users = User.objects.filter(
                models.Q(sent_messages__room=self) | models.Q(mentions__message__room=self)
            ).distinct()
            return message_users
    
    class Meta:
        verbose_name = 'Чат-кімната'
        verbose_name_plural = 'Чат-кімнати'
        ordering = ['-created_at']


class Message(models.Model):
    """Model for chat messages"""
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='messages', verbose_name='Кімната')
    sender = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='sent_messages', verbose_name='Відправник'
    )
    content = models.TextField(verbose_name='Текст повідомлення')
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='Час відправлення')
    is_read = models.BooleanField(default=False, verbose_name='Прочитано')
    mentions = models.ManyToManyField(
        User, related_name='mentions', blank=True, verbose_name='Згадки'
    )
    
    def __str__(self):
        return f"Повідомлення від {self.sender.username} о {self.timestamp}"
    
    class Meta:
        verbose_name = 'Повідомлення'
        verbose_name_plural = 'Повідомлення'
        ordering = ['timestamp']


class UserChatStatus(models.Model):
    """Model to track user's last read message in each chat room"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_statuses', verbose_name='Користувач')
    room = models.ForeignKey(ChatRoom, on_delete=models.CASCADE, related_name='user_statuses', verbose_name='Кімната')
    last_read_message = models.ForeignKey(
        Message, on_delete=models.SET_NULL, null=True, blank=True, 
        related_name='+', verbose_name='Останнє прочитане повідомлення'
    )
    last_visited = models.DateTimeField(auto_now=True, verbose_name='Останній візит')
    
    def unread_count(self):
        """Count unread messages in this room for this user"""
        if not self.last_read_message:
            return self.room.messages.count()
        
        return self.room.messages.filter(timestamp__gt=self.last_read_message.timestamp).count()
    
    def __str__(self):
        return f"Статус чату {self.room} для {self.user.username}"
    
    class Meta:
        verbose_name = 'Статус чату користувача'
        verbose_name_plural = 'Статуси чату користувачів'
        unique_together = ['user', 'room']
