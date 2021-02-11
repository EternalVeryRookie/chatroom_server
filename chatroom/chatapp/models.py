from typing import Final
from users.models import UserName
from django.db import models

# Create your models here.


class Chatroom(models.Model):
    room_name = models.CharField(max_length=100)
    create_date = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    create_user = models.ForeignKey(UserName, on_delete=models.SET_NULL, null=True)
    is_public = models.BooleanField(default=False)


class MemberRoles(models.TextChoices):
    GUEST = "GU", "Guest"
    MANAGER = "MA", "Manager"
    OWNER = "OW", "Owner"


class ChatroomMember(models.Model):
    room = models.ForeignKey(Chatroom, on_delete=models.CASCADE)
    user = models.ForeignKey(UserName, on_delete=models.SET_NULL, null=True)
    role = models.CharField(
        max_length=2,
        choices=MemberRoles.choices,
        default=MemberRoles.GUEST,
    )


class ChatMessage(models.Model):
    sender = models.ForeignKey(UserName, on_delete=models.SET_NULL, null=True)
    room = models.ForeignKey(Chatroom, on_delete=models.CASCADE)
    # content
    MAX_TEXT_LENGTH: Final[int] = 2048
    text = models.CharField(
        max_length=MAX_TEXT_LENGTH,
        error_messages= {
            "max_length": f"メッセージの文字数の上限は{MAX_TEXT_LENGTH}です"
        }
    )