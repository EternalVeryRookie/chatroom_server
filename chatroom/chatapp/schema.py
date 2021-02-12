from django_filters.filters import ChoiceFilter
from graphene_django.types import ErrorType
from .models import Chatroom, ChatroomMember, MemberRoles
import graphene
from graphene import relay
from graphql_relay import from_global_id
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
import django_filters

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
            "is_public": ["exact"]
        }


class ChatroomNode(DjangoObjectType):
    class Meta:
        model = Chatroom
        filterset_class = ChatroomFilter
        interfaces = (relay.Node, )

    @classmethod
    def get_queryset(cls, queryset, info):
        request_user = Auth(info.context).current_user

        #privateルームは作成者にのみ閲覧可能な状態
        #todo 権限を与えられたユーザーなら閲覧可能にする
        return  queryset.filter(is_public=True, is_active=True) \
            | queryset.filter(is_public=False, is_active=True, create_user=request_user)


class Query(graphene.ObjectType):
    chatroom = relay.Node.Field(ChatroomNode)
    all_chatrooms = DjangoFilterConnectionField(ChatroomNode)


class CreateChatroom(graphene.Mutation):
    class Arguments:
        name = graphene.String()
        is_public = graphene.Boolean()

    ok = graphene.Boolean()
    errors = graphene.List(Error)
    chatroom = graphene.Field(ChatroomNode)

    @classmethod
    def mutate(cls, root, info, name:str, is_public:bool):
        auth = Auth(info.context)
        if not auth.is_sign_in:
            return CreateChatroom(ok=False, errors=[Error(message="サインインしてください", error_type="not auth")])

        chatroom = Chatroom.objects.create(
            room_name=name,
            create_user=auth.current_user,
            is_public=is_public
        )

        return CreateChatroom(ok=True, errors=None, chatroom=chatroom)


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



class Mutation(graphene.ObjectType):
    create_chatroom = CreateChatroom.Field()
    rename_room_name = RenameRoomName.Field()
    delete_room = DeleteRoom().Field()


schema = graphene.Schema(query=Query, mutation=Mutation)
