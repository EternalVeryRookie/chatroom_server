from typing import Final
from users.models import UserName
from django.db import models

# Create your models here.

class AbstructChatroom(models.Model):
    room_name = models.CharField(max_length=100)
    create_date = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    create_user = models.ForeignKey(UserName, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.room_name

    class Meta:
        abstract = True


class Chatroom(AbstructChatroom):
    pass


class PrivateChatroom(AbstructChatroom):
    password = models.CharField(max_length=512)


class MemberRoles(models.TextChoices):
    GUEST = "GU", "Guest"
    MANAGER = "MA", "Manager"
    OWNER = "OW", "Owner"


class AbstractChatroomMember(models.Model):
    user = models.ForeignKey(UserName, on_delete=models.SET_NULL, null=True)
    is_enter = models.BooleanField(default=False)
    role = models.CharField(
        max_length=2,
        choices=MemberRoles.choices,
        default=MemberRoles.GUEST,
    )

    class Meta:
        abstract = True


class ChatroomMember(AbstractChatroomMember):
    room = models.ForeignKey(Chatroom, on_delete=models.CASCADE)

    
class PrivateChatroomMember(AbstractChatroomMember):
    room = models.ForeignKey(PrivateChatroom, on_delete=models.CASCADE)


class AbstractMessage(models.Model):
    sender = models.ForeignKey(UserName, on_delete=models.SET_NULL, null=True)
    send_date = models.DateTimeField(auto_now_add=True)
    
    MAX_TEXT_LENGTH: Final[int] = 2048
    text = models.CharField(
        max_length=MAX_TEXT_LENGTH,
        error_messages= {
            "max_length": f"メッセージの文字数の上限は{MAX_TEXT_LENGTH}です"
        }
    )

    class Meta:
        abstract = True


class ChatMessage(AbstractMessage):
    room = models.ForeignKey(Chatroom, on_delete=models.CASCADE)
    

class PrivateChatMessage(AbstractMessage):
    room = models.ForeignKey(PrivateChatroom, on_delete=models.CASCADE)
    