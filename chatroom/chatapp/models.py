from typing import Final

from django.core.exceptions import ValidationError

from users.models import UserName
from django.db import models, transaction


def validate_image(image: models.fields.files.ImageFieldFile):
    LIMIT_BYTE = 5 * 1000 * 1000 #5MB
    if image.size > LIMIT_BYTE:
        raise ValidationError("サイズが大きすぎます")


class UserProfile(models.Model):
    user = models.OneToOneField(UserName, on_delete=models.CASCADE)
    self_introduction = models.CharField(max_length=256, blank=True)
    icon = models.ImageField(upload_to="uploads/", validators=[validate_image])
    cover_image = models.ImageField(upload_to="uploads/", validators=[validate_image])


class AbstractChatroom(models.Model):
    room_name = models.CharField(max_length=100)
    create_date = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    create_user = models.ForeignKey(UserName, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return self.room_name

    class Meta:
        abstract = True


class Chatroom(AbstractChatroom):
    @classmethod
    def create(cls, name: str, create_user: UserName):
        with transaction.atomic():
            chatroom: Chatroom = cls.objects.create(
                room_name=name,
                create_user=create_user
            )
            
            member = ChatroomMember()
            member.room = chatroom
            member.user = create_user
            member.role = MemberRoles.OWNER
            member.save()

        return chatroom


class PrivateChatroom(AbstractChatroom):
    @classmethod
    def create(cls, name: str, create_user: UserName):
        with transaction.atomic():
            chatroom: PrivateChatroom = cls.objects.create(
                room_name=name,
                create_user=create_user
            )
            
            member = PrivateChatroomMember()
            member.room = chatroom
            member.user = create_user
            member.role = MemberRoles.OWNER
            member.save()

        return chatroom


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

    def allow_update_room(self) -> bool:
        """
        roomの情報を更新する権限があるかどうかを確認する
        """
        return self.role != MemberRoles.GUEST

    def allow_delete_room(self) -> bool:
        """
        roomを削除する権限があるかどうかを確認する
        """
        return self.user == self.room.create_user


class PrivateChatroomMember(AbstractChatroomMember):
    room = models.ForeignKey(PrivateChatroom, on_delete=models.CASCADE)

    def allow_update_room(self) -> bool:
        """
        roomの情報を更新する権限があるかどうかを確認する
        """
        return self.role != MemberRoles.GUEST

    def allow_delete_room(self) -> bool:
        """
        roomを削除する権限があるかどうかを確認する
        """
        return self.user == self.room.create_user


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
    