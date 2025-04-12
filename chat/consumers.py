import json
import re
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth.models import User
from .models import ChatRoom, Message, UserChatStatus
from django.utils import timezone


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_id = self.scope['url_route']['kwargs']['room_id']
        self.room_group_name = f'chat_{self.room_id}'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        # Accept the connection
        await self.accept()
        
        # Update user status on connect
        if self.scope['user'].is_authenticated:
            await self.update_user_status()
            
            # Fetch recent messages
            messages = await self.get_recent_messages()
            await self.send(text_data=json.dumps({
                'type': 'history',
                'messages': messages
            }))

    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )

    async def receive(self, text_data):
        """Handle messages from WebSocket"""
        data = json.loads(text_data)
        message_type = data.get('type', 'message')
        
        if message_type == 'message' and self.scope['user'].is_authenticated:
            content = data['message']
            
            # Extract mentions (usernames preceded by @)
            mention_usernames = re.findall(r'@(\w+)', content)
            
            # Store the message and get formatted data
            message_data = await self.save_message(content, mention_usernames)
            
            # Send message to room group
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'chat_message',
                    **message_data
                }
            )
            
            # If there are mentions, send notification to mentioned users
            if message_data.get('mentions'):
                await self.send_mention_notifications(message_data)
        
        elif message_type == 'read' and self.scope['user'].is_authenticated:
            # Mark messages as read up to a certain point
            message_id = data.get('message_id')
            if message_id:
                await self.mark_messages_read(message_id)

    async def chat_message(self, event):
        """Receive message from room group and send to WebSocket"""
        # Remove the message type key before sending to the client
        message_data = {k: v for k, v in event.items() if k != 'type'}
        
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'type': 'message',
            **message_data
        }))

    @database_sync_to_async
    def save_message(self, content, mention_usernames):
        """Save a message to the database and return formatted data"""
        # Get the chat room
        room = ChatRoom.objects.get(id=self.room_id)
        
        # Create a new message
        message = Message.objects.create(
            room=room,
            sender=self.scope['user'],
            content=content,
            is_read=False
        )
        
        # Add mentions if any
        mentioned_users = []
        if mention_usernames:
            users = User.objects.filter(username__in=mention_usernames)
            message.mentions.add(*users)
            
            # Format mention data for the response
            mentioned_users = [
                {
                    'id': user.id,
                    'username': user.username,
                    'name': user.get_full_name() or user.username
                }
                for user in users
            ]
        
        # Format the message data for response
        formatted_message = {
            'id': message.id,
            'room_id': room.id,
            'sender_id': self.scope['user'].id,
            'sender_name': self.scope['user'].get_full_name() or self.scope['user'].username,
            'content': content,
            'timestamp': message.timestamp.isoformat(),
            'mentions': mentioned_users
        }
        
        return formatted_message

    @database_sync_to_async
    def get_recent_messages(self, limit=50):
        """Get recent messages from the room"""
        room = ChatRoom.objects.get(id=self.room_id)
        messages = room.messages.select_related('sender').prefetch_related('mentions').order_by('-timestamp')[:limit]
        
        # Format messages for the client
        formatted_messages = []
        for message in reversed(list(messages)):  # Reverse to get oldest first
            formatted_messages.append({
                'id': message.id,
                'room_id': room.id,
                'sender_id': message.sender.id,
                'sender_name': message.sender.get_full_name() or message.sender.username,
                'content': message.content,
                'timestamp': message.timestamp.isoformat(),
                'mentions': [
                    {
                        'id': user.id,
                        'username': user.username,
                        'name': user.get_full_name() or user.username
                    }
                    for user in message.mentions.all()
                ]
            })
        
        return formatted_messages

    @database_sync_to_async
    def update_user_status(self):
        """Update the user's chat status for this room"""
        room = ChatRoom.objects.get(id=self.room_id)
        
        # Get or create user chat status for this room
        chat_status, created = UserChatStatus.objects.get_or_create(
            user=self.scope['user'],
            room=room
        )
        
        # Update the last visited timestamp
        chat_status.last_visited = timezone.now()
        chat_status.save()
        
        return chat_status

    @database_sync_to_async
    def mark_messages_read(self, message_id):
        """Mark messages as read up to the given message ID"""
        try:
            room = ChatRoom.objects.get(id=self.room_id)
            message = Message.objects.get(id=message_id, room=room)
            
            # Update the user's last read message
            chat_status, created = UserChatStatus.objects.get_or_create(
                user=self.scope['user'],
                room=room
            )
            chat_status.last_read_message = message
            chat_status.save()
            
            # Mark messages as read
            Message.objects.filter(
                room=room,
                timestamp__lte=message.timestamp,
                is_read=False
            ).update(is_read=True)
            
            return True
        except (ChatRoom.DoesNotExist, Message.DoesNotExist):
            return False

    async def send_mention_notifications(self, message_data):
        """Send notifications to mentioned users"""
        for mention in message_data.get('mentions', []):
            # Create a notification group name for the mentioned user
            user_notification_group = f"user_notifications_{mention['id']}"
            
            # Send to the user's notification group
            await self.channel_layer.group_send(
                user_notification_group,
                {
                    'type': 'chat_notification',
                    'message_id': message_data['id'],
                    'room_id': message_data['room_id'],
                    'sender_name': message_data['sender_name'],
                    'content': message_data['content']
                }
            )

    async def chat_notification(self, event):
        """Receive notification and send to WebSocket"""
        # This would be handled by a separate consumer for user notifications
        pass


class NotificationConsumer(AsyncWebsocketConsumer):
    """Consumer for handling real-time notifications to users"""
    
    async def connect(self):
        if not self.scope['user'].is_authenticated:
            await self.close()
            return
        
        # Create a notification group for this user
        self.user_id = self.scope['user'].id
        self.notification_group_name = f"user_notifications_{self.user_id}"
        
        # Join notification group
        await self.channel_layer.group_add(
            self.notification_group_name,
            self.channel_name
        )
        
        # Accept the connection
        await self.accept()

    async def disconnect(self, close_code):
        # Leave notification group
        if hasattr(self, 'notification_group_name'):
            await self.channel_layer.group_discard(
                self.notification_group_name,
                self.channel_name
            )

    async def chat_notification(self, event):
        """Receive notification from chat and send to WebSocket"""
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'notification_type': 'chat_mention',
            'message_id': event['message_id'],
            'room_id': event['room_id'],
            'sender_name': event['sender_name'],
            'content': event['content'],
            'timestamp': timezone.now().isoformat()
        }))
