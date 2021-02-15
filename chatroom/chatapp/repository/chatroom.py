from typing import List, Type
from django.http.request import HttpRequest
from chatapp.models import AbstractChatroomMember, PrivateChatroom, PrivateChatroomMember, Chatroom, ChatroomMember, MemberRoles, AbstractChatroom
from users.auth.auth import Auth
from users.models import UserName


def create_public_chatroom(name: str, request: HttpRequest) -> Chatroom:
    auth = Auth(request)
    if not auth.is_sign_in:
        raise Exception("サインインしてください")

    return Chatroom.create(name, auth.current_user)


def create_private_chatroom(name: str, request: HttpRequest) -> PrivateChatroom:
    auth = Auth(request)
    if not auth.is_sign_in:
        raise Exception("サインインしてください")
    
    return PrivateChatroom.create(name=name, create_user=auth.current_user)


def invitation(room_id: str, user_ids: List[str], request: HttpRequest):
    auth = Auth(request)
    if not auth.is_sign_in:
        raise Exception("サインインしてください")

    private_room = PrivateChatroom.objects.get(pk=room_id)
    query = PrivateChatroomMember.objects.filter(user=auth.current_user, room=private_room)
    if len(query) == 0 :
        # 招待を送ろうとしたユーザー自体がprivate roomに招待されていないということだが
        # その場合はルームの存在自体を知らせたくないため、「ルームが存在しない」旨のエラーをリターンする
        Exception("指定のルームは存在しません")

    member: PrivateChatroomMember = query[0]
    if not member.allow_update_room():
        raise Exception("権限がありません")

    for user_id in user_ids:
        user: UserName = UserName.objects.get(pk=user_id)
        PrivateChatroomMember(user=user, room=private_room, role=MemberRoles.GUEST).save()


def disable_public_room(room_id, request: HttpRequest) -> None:
    auth = Auth(request)
    if not auth.is_sign_in:
        raise Exception("サインインしてください")

    room: Chatroom = Chatroom.objects.get(pk=room_id)
    member: ChatroomMember = ChatroomMember.objects.get(user=auth.current_user, room=room)
    if not member.allow_delete_room():
        raise Exception("権限がありません")

    room.is_active = False
    room.save()


def rename_room(room_id, new_name: str, request: HttpRequest, cls: Type[AbstractChatroom], member: Type[AbstractChatroomMember])->AbstractChatroom:
    auth = Auth(request)
    if not auth.is_sign_in:
        raise Exception("サインインしてください")

    room: AbstractChatroom = cls.objects.get(pk=room_id)
    member: AbstractChatroomMember = member.objects.get(user=auth.current_user, room=room)
    if not member.allow_update_room():
        raise Exception("権限がありません")

    room.room_name = new_name
    room.save()

    return room


def rename_public_room(room_id: str, new_name: str, request: HttpRequest) -> Chatroom:
    return rename_room(room_id, new_name, request, Chatroom, ChatroomMember)


def rename_private_room(room_id: str, new_name: str, request: HttpRequest) -> PrivateChatroom:
    try:
        return rename_room(room_id, new_name, request, PrivateChatroom, PrivateChatroomMember)
    except PrivateChatroomMember.DoesNotExist:
        pass

    raise Exception("指定のルームは存在しません")