from inspect import currentframe
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone
from .models import Chatroom, ChatroomMember, MemberRoles, PrivateChatroom, PrivateChatroomMember
from users.schema import UserNameNode
from users.models import UserName

import graphene
from graphene import relay
from graphql_relay import from_global_id
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
import django_filters
import hashlib
import hmac

from users.auth.auth import Auth
from errors.graphql_errors import Error


class ChatroomFilter(django_filters.FilterSet):
    class Meta:
        model = Chatroom
        fields =  {
            "room_name": ["exact", "icontains", "istartswith"],
            "create_date": ["exact"],
            "is_active": ["exact"],
            "create_user": ["exact"],
        }


class ChatroomNode(DjangoObjectType):
    class Meta:
        model = Chatroom
        filter_fields  =  {
            "room_name": ["exact", "icontains", "istartswith"],
            "create_date": ["exact"],
            "is_active": ["exact"],
            "create_user": ["exact"],
        }        
        interfaces = (relay.Node, )


class PrivateChatroomNode(DjangoObjectType):
    class Meta:
        model = PrivateChatroom
        filter_fields  =  {
            "room_name": ["exact", "icontains", "istartswith"],
            "create_date": ["exact"],
            "is_active": ["exact"],
            "create_user": ["exact"],
        } 
        interfaces = (relay.Node, )
        exclude = ("password",)

    @classmethod
    def get_queryset(cls, queryset, info):
        auth = Auth(info.context)
        return queryset.filter(create_user=auth.current_user)
        

class Query(graphene.ObjectType):
    chatroom = relay.Node.Field(ChatroomNode)
    all_chatrooms = DjangoFilterConnectionField(ChatroomNode)
    all_private_rooms = DjangoFilterConnectionField(PrivateChatroomNode)


def check_authorization():
    pass


class CreateChatroom(graphene.Mutation):
    class Arguments:
        name = graphene.String()

    ok = graphene.Boolean()
    errors = graphene.List(Error)
    chatroom = graphene.Field(ChatroomNode)

    @classmethod
    def mutate(cls, root, info, name:str):
        auth = Auth(info.context)
        if not auth.is_sign_in:
            return CreateChatroom(ok=False, errors=[Error(message="サインインしてください", error_type="not auth")])

        chatroom = Chatroom.objects.create(
            room_name=name,
            create_user=auth.current_user
        )

        member = ChatroomMember()
        member.room = chatroom
        member.user = auth.current_user
        member.role = MemberRoles.OWNER
        member.save()

        return CreateChatroom(ok=True, errors=None, chatroom=chatroom)


class CreatePrivateChatroom(graphene.Mutation):
    class Arguments:
        name = graphene.String()
        password = graphene.String()

    ok = graphene.Boolean()
    errors = graphene.List(Error)

    
    @classmethod
    def mutate(cls, root, info, name:str, password:str):
        auth = Auth(info.context)
        if not auth.is_sign_in:
            return CreateChatroom(ok=False, errors=[Error(message="サインインしてください", error_type="not auth")])
        
        hashed_password = make_password(password)
        chatroom = PrivateChatroom(room_name=name, create_user=auth.current_user, password=hashed_password)
        chatroom.save()

        member = ChatroomMember()
        member.room = chatroom
        member.user = auth.current_user
        member.role = MemberRoles.OWNER
        member.save()

        return CreateChatroom(ok=True, errors=None, chatroom=chatroom)


#todo
# リクエストユーザーがゲストの場合 -> 認可系エラー
# 招待対象のユーザーが既に招待されている場合 -> 何もしない。エラーも返さない。
# リクエストユーザー自体がprivate roomに招待されていない場合 -> ルームが存在しなかった旨のエラーを返す
class InvitationUser(relay.ClientIDMutation):
    class Input:
        users = graphene.List(graphene.ID)
        room = graphene.ID()

    ok = graphene.Boolean()
    errors = graphene.List(Error)

    @classmethod
    def mutate_and_get_payload(cls, root, info, users, room):
        current_user = Auth(info.context).current_user
        t, private_room_id = from_global_id(room)
        private_room = PrivateChatroom.objects.get(pk=private_room_id)
        
        #ゲストに招待権限はない
        try:
            if PrivateChatroomMember.objects.get(user=current_user, room=private_room).role == MemberRoles.GUEST:
                err = Error(message="ユーザーを招待する権限がありません")
                return InvitationUser(ok=False, errors=[err])
        except PrivateChatroomMember.DoesNotExist:
            err = Error(message="指定のルームは存在しません")
            return InvitationUser(ok=False, errors=[err])

        for id in users:
            t, primary_id = from_global_id(id)
            user = UserName.objects.get(pk=primary_id)
            PrivateChatroomMember(user=user, room=private_room, is_enter=False, role=MemberRoles.GUEST).save()


class RenameRoomName(relay.ClientIDMutation):
    class Input:
        new_name = graphene.String()
        id = graphene.ID()

    ok = graphene.Boolean()
    errors = graphene.List(Error)
    chatroom = graphene.Field(ChatroomNode)

    @classmethod
    def mutate_and_get_payload(cls, root, info, new_name, id):
        try:
            t, primary_id = from_global_id(id)
        except UnicodeDecodeError:
            err = Error(message= f"id「{id}」のルームが見つかりませんでした", error_type="Chatroom.DoesNotExist")
            return RenameRoomName(ok=False, errors=[err], chatroom=None)

        if t != "ChatroomNode":
            err = Error(message= f"id「{id}」のルームが見つかりませんでした", error_type="Chatroom.DoesNotExist")
            return RenameRoomName(ok=False, errors=[err], chatroom=None)
            
        try:
            room = Chatroom.objects.get(pk=primary_id)
        except Chatroom.DoesNotExist:
            err = Error(message= f"id「{id}」のルームが見つかりませんでした", error_type="Chatroom.DoesNotExist")
            return RenameRoomName(ok=False, errors=[err], chatroom=None)

        auth = Auth(info.context)
        is_allow_mutate = auth.is_same_user(room.create_user)
        if not(is_allow_mutate):
            try:
                member = ChatroomMember.objects.filter(user__username=auth.current_user.username).get(room=room)
                is_allow_mutate = member.role != MemberRoles.GUEST
            except ChatroomMember.DoesNotExist:
                pass

        if is_allow_mutate:
            room.room_name = new_name
            room.save()

            return RenameRoomName(ok=True, errors=None, chatroom=room)
        else:
            #実際は認証エラーだが、権限のないユーザーにはルームが存在していることも知らせたくない
            err = Error(message= f"id「{id}」のルームが見つかりませんでした", error_type="Chatroom.DoesNotExist")
            return RenameRoomName(ok=False, errors=[err], chatroom=None)


class DeleteRoom(relay.ClientIDMutation):
    class Input:
        id = graphene.ID()

    ok = graphene.Boolean()
    errors = graphene.List(Error)
    
    @classmethod
    def mutate_and_get_payload(cls, root, info, id):
        try:
            t, primary_id = from_global_id(id)
        except UnicodeDecodeError:
            err = Error(message= f"id「{id}」のルームが見つかりませんでした", error_type="Chatroom.DoesNotExist")
            return DeleteRoom(ok=False, errors=[err])

        if t != "ChatroomNode":
            err = Error(message= f"id「{id}」のルームが見つかりませんでした", error_type="Chatroom.DoesNotExist")
            return DeleteRoom(ok=False, errors=[err])
            
        try:
            room = Chatroom.objects.get(pk=primary_id, is_active=True)
        except Chatroom.DoesNotExist:
            err = Error(message= f"id「{id}」のルームが見つかりませんでした", error_type="Chatroom.DoesNotExist")
            return DeleteRoom(ok=False, errors=[err])

        if Auth(info.context).is_same_user(room.create_user):
            room.is_active = False
            room.save()
            return DeleteRoom(ok=True, errors=None)
        else:
            #実際は認証エラーだが、権限のないユーザーにはルームが存在していることも知らせたくない
            err = Error(message= f"id「{id}」のルームが見つかりませんでした", error_type="Chatroom.DoesNotExist")
            return DeleteRoom(ok=False, errors=[err])


class EnterChatroom(graphene.ClientIDMutation):
    class Input:
        room_id = graphene.ID()

    ok = graphene.Boolean()
    errors = graphene.List(Error)
    
    @classmethod
    def mutate_and_get_payload(cls, root, info, room_id):
        try:
            t, room_pk = from_global_id(room_id)
            if t != "ChatroomNode":
                err = Error(message="指定のルームは存在しません")
                return EnterChatroom(ok=False, errors=[err])
        except UnicodeDecodeError:
            err = Error(message="指定のルームは存在しません")
            return EnterChatroom(ok=False, errors=[err])
        except Exception as e:
            err = Error(message="エラー")
            return EnterChatroom(ok=False, errors=[err])
        
        #ここでuserにroomに入る権限があるかを確認する
        auth = Auth(info.context)
        user: UserName = auth.current_user
        room = Chatroom.objects.get(pk=room_pk)
        try:
            member = ChatroomMember.objects.get(user=user, room=room)
            #publicならok、privateでも作成者と許可されたユーザーならok
            member.is_enter = True
            member.save()
        except ChatroomMember.DoesNotExist:
            member = ChatroomMember(user=user, room=room)
            member.is_enter = True
            member.save()

        return EnterChatroom(ok=True, errors=None)


class ExitChatroom(graphene.ClientIDMutation):
    class Input:
        room_id = graphene.ID()

    ok = graphene.Boolean()
    errors = graphene.List(Error)
    
    @classmethod
    def mutate_and_get_payload(cls, root, info, room_id):
        try:
            t, room_pk = from_global_id(room_id)
            if t != "ChatroomNode":
                err = Error(message="指定のルームは存在しません")
                return EnterChatroom(ok=False, errors=[err])
        except UnicodeDecodeError:
            err = Error(message="指定のルームは存在しません")
            return EnterChatroom(ok=False, errors=[err])
        except Exception as e:
            err = Error(message="エラー")
            return EnterChatroom(ok=False, errors=[err])

        room = Chatroom.objects.get(pk=room_pk)
        try:
            member = ChatroomMember.objects.get(user=user, room=room)
            member.is_enter = False
            member.save()
        except ChatroomMember.DoesNotExist:
            err = Error(message="指定のユーザは指定のルームに入室していません")
            return ExitChatroom(ok=False, errors=[err])

        return ExitChatroom(ok=True, errors=None)

class Mutation(graphene.ObjectType):
    create_chatroom = CreateChatroom.Field()
    create_private_chatroom = CreatePrivateChatroom.Field()
    rename_room_name = RenameRoomName.Field()
    delete_room = DeleteRoom().Field()
    enter_chatroom = EnterChatroom().Field()
    exit_chatroom = ExitChatroom().Field()


schema = graphene.Schema(query=Query, mutation=Mutation)
