from django.http import request
from graphql.error.base import GraphQLError
from .models import Chatroom, ChatroomMember, MemberRoles, PrivateChatroom, PrivateChatroomMember
from users.models import UserName
import chatapp.logic.chatroom_interactor as logic

import graphene
from graphene import relay
from graphql_relay import from_global_id
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
import django_filters

from users.auth.auth import Auth
from errors.graphql_error_decorator import reraise_graphql_error


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
    chatroom = graphene.Field(ChatroomNode)

    @reraise_graphql_error
    @classmethod
    def mutate(cls, root, info, name:str):
        room = logic.create_public_chatroom(info.context, name)

        return CreateChatroom(ok=True, chatroom=room)


class CreatePrivateChatroom(graphene.Mutation):
    class Arguments:
        name = graphene.String()

    ok = graphene.Boolean()
    
    @reraise_graphql_error
    @classmethod
    def mutate(cls, root, info, name:str):
        room = logic.create_public_chatroom(info.context, name)

        return CreatePrivateChatroom(ok=True, chatroom=room)


class InvitationUser(relay.ClientIDMutation):
    class Input:
        users = graphene.List(graphene.ID)
        room = graphene.ID()

    ok = graphene.Boolean()

    @reraise_graphql_error
    @classmethod
    def mutate_and_get_payload(cls, root, info, users, room):
        node_type, private_room_id = from_global_id(room)
        if node_type != "PrivateChatroomNode":
            raise Exception("指定のルームは存在しません")
        
        target_user_ids = [None] * len(users)
        for i, user_id in enumerate(users):
            node_type, primary_id = from_global_id(user_id)
            if node_type != "UserNameNode":
                raise Exception(f"指定のユーザー「{user_id}」は存在しません")
            
            target_user_ids[i] = primary_id

        logic.invitation(info.context, private_room_id, target_user_ids)
        return InvitationUser(ok=True)


class RenameRoomName(relay.ClientIDMutation):
    class Input:
        new_name = graphene.String()
        id = graphene.ID()

    ok = graphene.Boolean()
    chatroom = graphene.Field(ChatroomNode)

    @reraise_graphql_error
    @classmethod
    def mutate_and_get_payload(cls, root, info, new_name, id):
        try:
            node_type, primary_id = from_global_id(id)
        except UnicodeDecodeError as ude:
            raise Exception(f"id「{id}」のルームが見つかりませんでした") from ude

        if node_type != "ChatroomNode":
            raise Exception(f"id「{id}」のルームが見つかりませんでした")

        room = logic.rename_public_room(request, primary_id, new_name)
        return RenameRoomName(ok=True, chatroom=room)


class DeleteRoom(relay.ClientIDMutation):
    class Input:
        id = graphene.ID()

    ok = graphene.Boolean()

    @reraise_graphql_error
    @classmethod
    def mutate_and_get_payload(cls, root, info, id):
        try:
            node_type, primary_id = from_global_id(id)
        except UnicodeDecodeError as ude:
            raise Exception(f"id「{id}」のルームが見つかりませんでした") from ude

        if node_type != "ChatroomNode":
            raise Exception(f"id「{id}」のルームが見つかりませんでした")

        logic.disable_public_room(request=info.context, room_id=primary_id)

        return DeleteRoom(ok=True)


class EnterChatroom(graphene.ClientIDMutation):
    class Input:
        room_id = graphene.ID()

    ok = graphene.Boolean()
    connection_url = graphene.String()
    
    @reraise_graphql_error
    @classmethod
    def mutate_and_get_payload(cls, root, info, room_id):
        try:
            node_type, room_pk = from_global_id(room_id)
        except UnicodeDecodeError:
            raise Exception("指定のルームは存在しません")

        if node_type != "ChatroomNode":
            raise Exception("指定のルームは存在しません")

        logic.enter_public_room(request=info.context, room_id=room_pk)
        return EnterChatroom(ok=True, connection_url="websocket接続用のURLをreturnする")


class ExitChatroom(graphene.ClientIDMutation):
    class Input:
        room_id = graphene.ID()

    ok = graphene.Boolean()
    errors = graphene.List(Error)
    
    @reraise_graphql_error
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
