from typing import List, Type
from django.http.request import HttpRequest

from chatapp.models import AbstractChatroomMember, PrivateChatroom, PrivateChatroomMember, Chatroom, ChatroomMember, MemberRoles, AbstractChatroom
from users.auth.auth import Auth
from users.auth.decorator import require_sign_in
from users.models import UserName


@require_sign_in
def create_public_chatroom(request: HttpRequest, name: str) -> Chatroom:
    return Chatroom.create(name,  Auth(request).current_user)


@require_sign_in
def create_private_chatroom(request: HttpRequest, name: str) -> PrivateChatroom:
    return PrivateChatroom.create(name=name, create_user= Auth(request).current_user)


@require_sign_in
def invitation(request: HttpRequest, room_id: str, user_ids: List[str]):
    auth = Auth(request)

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


@require_sign_in
def __disable_room(request: HttpRequest, room_id, room_type: Type[AbstractChatroom], member_type: Type[AbstractChatroomMember]) -> None:
    auth = Auth(request)

    room: room_type = room_type.objects.get(pk=room_id)
    member: member_type = member_type.objects.get(user=auth.current_user, room=room)
    if not member.allow_delete_room():
        raise Exception("権限がありません")

    room.is_active = False
    room.save()


def disable_public_room(request: HttpRequest, room_id) -> None:
    __disable_room(request, room_id, Chatroom, ChatroomMember)


def disable_private_room(request: HttpRequest, room_id) -> None:
    __disable_room(request, room_id, PrivateChatroom, PrivateChatroomMember)


@require_sign_in
def __rename_room(
    request: HttpRequest,
    room_id,
    new_name: str,
    cls: Type[AbstractChatroom],
    member: Type[AbstractChatroomMember]
    )->AbstractChatroom:

    auth = Auth(request)

    room: AbstractChatroom = cls.objects.get(pk=room_id)
    member: AbstractChatroomMember = member.objects.get(user=auth.current_user, room=room)
    if not member.allow_update_room():
        raise Exception("権限がありません")

    room.room_name = new_name
    room.save()

    return room


def rename_public_room(request: HttpRequest, room_id: str, new_name: str) -> Chatroom:
    return __rename_room(request, room_id, new_name, Chatroom, ChatroomMember)


def rename_private_room(request: HttpRequest, room_id: str, new_name: str) -> PrivateChatroom:
    """
    privateルームに招待されていないメンバーがrenameを行おうとした場合、
    ルームの存在自体を知らせたくないため、「指定のルームは存在しません」というエラーを返す
    """
    try:
        return __rename_room(request, room_id, new_name, PrivateChatroom, PrivateChatroomMember)
    except PrivateChatroomMember.DoesNotExist:
        pass

    raise Exception("指定のルームは存在しません")


#todo ここでwebsocket通信を確立する
def __enter_room(request: HttpRequest, room_id: str, room_type: Type[AbstractChatroom], member_type: Type[AbstractChatroomMember]) -> None:
    room = room_type.objects.get(pk=room_id)
    user = Auth(request).current_user
    member_query = member_type.objects.filter(user=user, room=room)
    if len(member_query) == 0:
        member_type.objects.create(user=user, is_enter=True, role=MemberRoles.GUEST, room=room)
    else:
        member_query[0].is_enter = True
        member_query[0].save()


def enter_public_room(request: HttpRequest, room_id: str):
    __enter_room(request, room_id, Chatroom, ChatroomMember)


def enter_private_room(request: HttpRequest, room_id: str):
    __enter_room(request, room_id, PrivateChatroom, PrivateChatroomMember)


