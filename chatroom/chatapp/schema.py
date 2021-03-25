import graphene
from graphql_relay import from_global_id
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
import django_filters

from .models import Chatroom, PrivateChatroom

from users.schema import UserNameNode
from users.models import UserName
from common.nodes.url_safe_encode_node import UrlSafeEncodeNode
from .logic import chatroom_interactor as logic
from users.auth.auth import Auth
from common.errors.graphql_error_decorator import reraise_graphql_error


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
        #filterset_class = ChatroomFilter
        filter_fields =  {
            "room_name": ["exact", "icontains", "istartswith"],
            "create_date": ["exact"],
            "is_active": ["exact"],
            "create_user": ["exact"],
        }
        interfaces = (UrlSafeEncodeNode, )


class PrivateChatroomNode(DjangoObjectType):
    class Meta:
        model = PrivateChatroom
        #filterset_class = ChatroomFilter
        filter_fields =  {
            "room_name": ["exact", "icontains", "istartswith"],
            "create_date": ["exact"],
            "is_active": ["exact"],
            "create_user": ["exact"],
        }
        interfaces = (UrlSafeEncodeNode, )

    @classmethod
    def get_queryset(cls, queryset, info):
        auth = Auth(info.context)

        return queryset.filter(privatechatroommember__user=auth.current_user)


class Query(graphene.ObjectType):
    chatroom = UrlSafeEncodeNode.Field(ChatroomNode)
    all_chatrooms = DjangoFilterConnectionField(ChatroomNode)
    exclude_joined_public_chatroom = DjangoFilterConnectionField(ChatroomNode)
    all_private_rooms = DjangoFilterConnectionField(PrivateChatroomNode)
    current_user_joined_public_chatroom = DjangoFilterConnectionField(ChatroomNode)
    current_user_joined_private_chatroom = DjangoFilterConnectionField(PrivateChatroomNode)

    def resolve_current_user_joined_public_chatroom(root, info, **kwargs):
        return Chatroom.objects.filter(chatroommember__user=Auth(info.context).current_user, chatroommember__is_enter=True)

    def resolve_current_user_joined_private_chatroom(root, info, **kwargs):
        return PrivateChatroom.objects.filter(privatechatroommember__user=Auth(info.context).current_user, privatechatroommember__is_enter=True)

    def resolve_exclude_joined_public_chatroom(root, info, **kwargs):
        return Chatroom.objects.exclude(chatroommember__user=Auth(info.context).current_user, chatroommember__is_enter=True)


class CreateChatroom(graphene.Mutation):
    class Arguments:
        name = graphene.String()
        description = graphene.String()

    ok = graphene.Boolean()
    chatroom = graphene.Field(ChatroomNode)

    @classmethod
    @reraise_graphql_error
    def mutate(cls, root, info, name:str, description:str):
        room = logic.create_public_chatroom(info.context, name)

        return CreateChatroom(ok=True, chatroom=room)


class CreatePrivateChatroom(graphene.Mutation):
    class Arguments:
        name = graphene.String()
        description = graphene.String()

    ok = graphene.Boolean()
    chatroom = graphene.Field(PrivateChatroomNode)

    @classmethod
    @reraise_graphql_error
    def mutate(cls, root, info, name:str, description:str):
        room = logic.create_private_chatroom(info.context, name)

        return CreatePrivateChatroom(ok=True, chatroom=room)


#todo publicルームにも招待機能を追加する
class InvitationUser(graphene.Mutation):
    class Arguments:
        users = graphene.List(graphene.ID)
        room = graphene.ID()

    ok = graphene.Boolean()

    @classmethod
    @reraise_graphql_error
    def mutate(cls, root, info, users, room):
        node_type, private_room_id = from_global_id(room)
        if node_type != str(PrivateChatroomNode):
            raise Exception("指定のルームは存在しません")
        
        target_user_ids = [None] * len(users)
        for i, user_id in enumerate(users):
            node_type, primary_id = from_global_id(user_id)
            if node_type != str(UserNameNode):
                raise Exception(f"指定のユーザー「{user_id}」は存在しません")
            
            target_user_ids[i] = primary_id

        logic.invitation(info.context, private_room_id, target_user_ids)
        return InvitationUser(ok=True)


class RenamePublicRoomName(graphene.Mutation):
    class Arguments:
        new_name = graphene.String()
        id = graphene.ID()

    ok = graphene.Boolean()
    chatroom = graphene.Field(ChatroomNode)

    @classmethod
    @reraise_graphql_error
    def mutate(cls, root, info, new_name, id):
        try:
            node_type, primary_id = from_global_id(id)
        except UnicodeDecodeError as ude:
            raise Exception(f"id「{id}」のルームが見つかりませんでした") from ude

        if node_type != str(ChatroomNode):
            raise Exception(f"id「{id}」のルームが見つかりませんでした")

        room = logic.rename_public_room(info.context, primary_id, new_name)
        return RenamePublicRoomName(ok=True, chatroom=room)


class RenamePrivateRoomName(graphene.Mutation):
    class Arguments:
        new_name = graphene.String()
        id = graphene.ID()

    ok = graphene.Boolean()
    chatroom = graphene.Field(PrivateChatroomNode)

    @classmethod
    @reraise_graphql_error
    def mutate(cls, root, info, new_name, id):
        try:
            node_type, primary_id = from_global_id(id)
        except UnicodeDecodeError as ude:
            raise Exception(f"id「{id}」のルームが見つかりませんでした") from ude

        if node_type != str(PrivateChatroomNode):
            raise Exception(f"id「{id}」のルームが見つかりませんでした")

        room = logic.rename_private_room(info.context, primary_id, new_name)
        return RenamePrivateRoomName(ok=True, chatroom=room)


class DeletePublicRoom(graphene.Mutation):
    class Arguments:
        id = graphene.ID()

    ok = graphene.Boolean()

    @classmethod
    @reraise_graphql_error
    def mutate(cls, root, info, id):
        try:
            node_type, primary_id = from_global_id(id)
        except UnicodeDecodeError as ude:
            raise Exception(f"id「{id}」のルームが見つかりませんでした") from ude

        if node_type != str(ChatroomNode):
            raise Exception(f"id「{id}」のルームが見つかりませんでした")

        logic.disable_public_room(request=info.context, room_id=primary_id)

        return DeletePublicRoom(ok=True)


class DeletePrivateRoom(graphene.Mutation):
    class Arguments:
        id = graphene.ID()

    ok = graphene.Boolean()

    @classmethod
    @reraise_graphql_error
    def mutate(cls, root, info, id):
        try:
            node_type, primary_id = from_global_id(id)
        except UnicodeDecodeError as ude:
            raise Exception(f"id「{id}」のルームが見つかりませんでした") from ude

        if node_type != str(PrivateChatroomNode):
            raise Exception(f"id「{id}」のルームが見つかりませんでした")

        logic.disable_private_room(request=info.context, room_id=primary_id)

        return DeletePrivateRoom(ok=True)


class EnterPublicChatroom(graphene.Mutation):
    class Arguments:
        room_id = graphene.ID()

    ok = graphene.Boolean()
    connection_url = graphene.String()
    
    @classmethod
    @reraise_graphql_error
    def mutate(cls, root, info, room_id):
        try:
            node_type, room_pk = from_global_id(room_id)
        except UnicodeDecodeError:
            raise Exception("指定のルームは存在しません")

        if node_type != "ChatroomNode":
            raise Exception("指定のルームは存在しません")

        logic.enter_public_room(request=info.context, room_id=room_pk)
        return EnterPublicChatroom(ok=True, connection_url="websocket接続用のURLをreturnする")


class EnterPrivateChatroom(graphene.Mutation):
    class Arguments:
        room_id = graphene.ID()

    ok = graphene.Boolean()
    connection_url = graphene.String()
    
    @classmethod
    @reraise_graphql_error
    def mutate(cls, root, info, room_id):
        try:
            node_type, room_pk = from_global_id(room_id)
        except UnicodeDecodeError:
            raise Exception("指定のルームは存在しません")

        if node_type != str(PrivateChatroomNode):
            raise Exception("指定のルームは存在しません")

        logic.enter_private_room(request=info.context, room_id=room_pk)
        return EnterPublicChatroom(ok=True, connection_url="websocket接続用のURLをreturnする")


class ExitChatroom(graphene.Mutation):
    class Arguments:
        room_id = graphene.ID()

    ok = graphene.Boolean()
    
    @classmethod
    @reraise_graphql_error
    def mutate(cls, root, info, room_id):
        try:
            node_type, room_pk = from_global_id(room_id)
        except UnicodeDecodeError as ude:
            raise Exception("指定のルームは存在しません") from ude

        if node_type == str(ChatroomNode):
            logic.exit_public_room(request=info.context, room_id=room_pk)
        elif node_type == str(PrivateChatroomNode):
            logic.exit_private_room(request=info.context, room_id=room_pk)
        else :
            raise Exception("指定のルームは存在しません")

        return ExitChatroom(ok=True)
        

class Mutation(graphene.ObjectType):
    create_public_chatroom = CreateChatroom.Field()
    create_private_chatroom = CreatePrivateChatroom.Field()
    invitation_user = InvitationUser.Field()
    rename_public_room_name = RenamePublicRoomName.Field()
    rename_private_room_name = RenamePrivateRoomName.Field()
    delete_public_room = DeletePublicRoom().Field()
    delete_private_room = DeletePrivateRoom().Field()
    enter_public_chatroom = EnterPublicChatroom().Field()
    enter_private_chatroom = EnterPrivateChatroom().Field()
    exit_chatroom = ExitChatroom().Field()

schema = graphene.Schema(query=Query, mutation=Mutation)
