import base64
import hashlib
from django.db.models import base

from django.db.models.fields.files import ImageFieldFile
import graphene
from graphene_django.fields import DjangoConnectionField
from graphene_file_upload.scalars import Upload
from graphene import relay
from graphql_relay import from_global_id
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
import django_filters

from django.db.models.fields.files import ImageFieldFile
from .models import Chatroom, PrivateChatroom, UserProfile

from nodes.url_safe_encode_node import UrlSafeEncodeNode
from .logic import chatroom_interactor as logic
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


class UserProfileNode(DjangoObjectType):
    class Meta:
        model = UserProfile
        fields = "__all__"
        interfaces = (UrlSafeEncodeNode, )

    def resolve_icon(self: UserProfile, info):
        image: ImageFieldFile = self.icon
        names = image.name.split(".")
        image.open(mode="rb")
        content = image.read()
        return f'data:image/{names[len(names)-1]};base64,{base64.b64encode(content).decode("utf-8")}'
        
    def resolve_cover_image(self: UserProfile, info):
        image: ImageFieldFile = self.cover_image
        names = image.name.split(".")
        image.open(mode="rb")
        content = image.read()
        return f'data:image/{names[len(names)-1]};base64,{base64.b64encode(content).decode("utf-8")}'
    

class Query(graphene.ObjectType):
    chatroom = UrlSafeEncodeNode.Field(ChatroomNode)
    user_profile = UrlSafeEncodeNode.Field(UserProfileNode)
    all_chatrooms = DjangoFilterConnectionField(ChatroomNode)
    exclude_joined_public_chatroom = DjangoFilterConnectionField(ChatroomNode)
    all_private_rooms = DjangoFilterConnectionField(PrivateChatroomNode)
    current_user_joined_public_chatroom = DjangoFilterConnectionField(ChatroomNode)
    current_user_joined_private_chatroom = DjangoFilterConnectionField(PrivateChatroomNode)
    all_profiles = DjangoConnectionField(UserProfileNode)
    current_user_profile = graphene.Field(UserProfileNode)

    def resolve_current_user_joined_public_chatroom(root, info, **kwargs):
        return Chatroom.objects.filter(chatroommember__user=Auth(info.context).current_user)

    def resolve_current_user_joined_private_chatroom(root, info, **kwargs):
        return PrivateChatroom.objects.filter(privatechatroommember__user=Auth(info.context).current_user)

    def resolve_exclude_joined_public_chatroom(root, info, **kwargs):
        return Chatroom.objects.exclude(chatroommember__user=Auth(info.context).current_user)

    def resolve_current_user_profile(root, info):
        current = Auth(info.context).current_user
        return UserProfile.objects.get(user = current)


class EditProfile(graphene.Mutation):
    class Arguments:
        self_introduction = graphene.String(required=False)
        icon = Upload(required=False)
        cover_image = Upload(required=False)

    success = graphene.Boolean()

    def mutate(self, info, **kwargs):
        kwargs["icon"]
        # do something with your file
        #UserProfile.objects.create(self_introduction="テストです", icon="")
        user = Auth(info.context).current_user
        try:
            profile: UserProfile = UserProfile.objects.get(user=user)
            if "self_introduction" in kwargs:
                profile.self_introduction = kwargs["self_introduction"]

            if "icon" in kwargs:
                profile.icon = kwargs["icon"]
                names = profile.icon.name.split(".")
                profile.icon.name = hashlib.md5(names[0].encode()).hexdigest() + "." + names[len(names)-1]

            if "cover_image" in kwargs:
                profile.cover_image = kwargs["cover_image"]
                names = profile.cover_image.name.split(".")
                profile.cover_image.name = hashlib.md5(names[0].encode()).hexdigest() + "." + names[len(names)-1]

        except UserProfile.DoesNotExist:
            profile = UserProfile(
                user=user, 
                self_introduction=kwargs.get("self_introduction", ""), 
                icon=kwargs.get("icon", None), 
                cover_image=kwargs.get("cover_image", None), 
            )

            if profile.icon:
                names = profile.icon.name.split(".")
                profile.icon.name = hashlib.md5(names[0].encode()).hexdigest() + "." + names[len(names)-1]

            if profile.cover_image:
                names = profile.cover_image.name.split(".")
                profile.cover_image.name = hashlib.md5(names[0].encode()).hexdigest() + "." + names[len(names)-1]

        profile.full_clean()
        profile.save() 

        return EditProfile(success=True)

class UploadsMutation(graphene.Mutation):
    class Arguments:
        file = graphene.List(Upload) 

    success = graphene.Boolean()

    def mutate(self, info, file, **kwargs):
        # do something with your file
        #UserProfile.objects.create(self_introduction="テストです", icon="")
        print(file)
        return UploadsMutation(success=True)


class CreateChatroom(graphene.Mutation):
    class Arguments:
        name = graphene.String()

    ok = graphene.Boolean()
    chatroom = graphene.Field(ChatroomNode)

    @classmethod
    @reraise_graphql_error
    def mutate(cls, root, info, name:str):
        room = logic.create_public_chatroom(info.context, name)

        return CreateChatroom(ok=True, chatroom=room)


class CreatePrivateChatroom(graphene.Mutation):
    class Arguments:
        name = graphene.String()

    ok = graphene.Boolean()
    chatroom = graphene.Field(PrivateChatroomNode)

    @classmethod
    @reraise_graphql_error
    def mutate(cls, root, info, name:str):
        room = logic.create_private_chatroom(info.context, name)

        return CreatePrivateChatroom(ok=True, chatroom=room)


#todo publicルームにも招待機能を追加する
class InvitationUser(relay.ClientIDMutation):
    class Input:
        users = graphene.List(graphene.ID)
        room = graphene.ID()

    ok = graphene.Boolean()

    @classmethod
    @reraise_graphql_error
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

    @classmethod
    @reraise_graphql_error
    def mutate_and_get_payload(cls, root, info, new_name, id):
        try:
            node_type, primary_id = from_global_id(id)
        except UnicodeDecodeError as ude:
            raise Exception(f"id「{id}」のルームが見つかりませんでした") from ude

        if node_type != str(ChatroomNode):
            raise Exception(f"id「{id}」のルームが見つかりませんでした")

        room = logic.rename_public_room(info.context, primary_id, new_name)
        return RenameRoomName(ok=True, chatroom=room)


class RenamePrivateRoomName(relay.ClientIDMutation):
    class Input:
        new_name = graphene.String()
        id = graphene.ID()

    ok = graphene.Boolean()
    chatroom = graphene.Field(PrivateChatroomNode)

    @classmethod
    @reraise_graphql_error
    def mutate_and_get_payload(cls, root, info, new_name, id):
        try:
            node_type, primary_id = from_global_id(id)
        except UnicodeDecodeError as ude:
            raise Exception(f"id「{id}」のルームが見つかりませんでした") from ude

        if node_type != str(PrivateChatroomNode):
            raise Exception(f"id「{id}」のルームが見つかりませんでした")

        room = logic.rename_private_room(info.context, primary_id, new_name)
        return RenamePrivateRoomName(ok=True, chatroom=room)



class DeleteRoom(relay.ClientIDMutation):
    class Input:
        id = graphene.ID()

    ok = graphene.Boolean()

    @classmethod
    @reraise_graphql_error
    def mutate_and_get_payload(cls, root, info, id):
        try:
            node_type, primary_id = from_global_id(id)
        except UnicodeDecodeError as ude:
            raise Exception(f"id「{id}」のルームが見つかりませんでした") from ude

        if node_type != str(ChatroomNode):
            raise Exception(f"id「{id}」のルームが見つかりませんでした")

        logic.disable_public_room(request=info.context, room_id=primary_id)

        return DeleteRoom(ok=True)


class EnterPublicChatroom(graphene.ClientIDMutation):
    class Input:
        room_id = graphene.ID()

    ok = graphene.Boolean()
    connection_url = graphene.String()
    
    @classmethod
    @reraise_graphql_error
    def mutate_and_get_payload(cls, root, info, room_id):
        try:
            node_type, room_pk = from_global_id(room_id)
        except UnicodeDecodeError:
            raise Exception("指定のルームは存在しません")

        if node_type != "ChatroomNode":
            raise Exception("指定のルームは存在しません")

        logic.enter_public_room(request=info.context, room_id=room_pk)
        return EnterPublicChatroom(ok=True, connection_url="websocket接続用のURLをreturnする")


class EnterPrivateChatroom(graphene.ClientIDMutation):
    class Input:
        room_id = graphene.ID()

    ok = graphene.Boolean()
    connection_url = graphene.String()
    
    @classmethod
    @reraise_graphql_error
    def mutate_and_get_payload(cls, root, info, room_id):
        try:
            node_type, room_pk = from_global_id(room_id)
        except UnicodeDecodeError:
            raise Exception("指定のルームは存在しません")

        if node_type != str(PrivateChatroomNode):
            raise Exception("指定のルームは存在しません")

        logic.enter_private_room(request=info.context, room_id=room_pk)
        return EnterPublicChatroom(ok=True, connection_url="websocket接続用のURLをreturnする")


class ExitChatroom(graphene.ClientIDMutation):
    class Input:
        room_id = graphene.ID()

    ok = graphene.Boolean()
    
    @classmethod
    @reraise_graphql_error
    def mutate_and_get_payload(cls, root, info, room_id):
        try:
            node_type, room_pk = from_global_id(room_id)
        except UnicodeDecodeError as ude:
            raise Exception("指定のルームは存在しません") from ude

        if node_type != "ChatroomNode":
            raise Exception("指定のルームは存在しません")

        logic.exit_public_room(request=info.context, room_id=room_pk)
        return ExitChatroom(ok=True)
        

class Mutation(graphene.ObjectType):
    create_public_chatroom = CreateChatroom.Field()
    create_private_chatroom = CreatePrivateChatroom.Field()
    invitation_user = InvitationUser.Field()
    rename_public_room_name = RenameRoomName.Field()
    rename_private_room_name = RenamePrivateRoomName.Field()
    delete_room = DeleteRoom().Field()
    enter_public_chatroom = EnterPublicChatroom().Field()
    enter_private_chatroom = EnterPrivateChatroom().Field()
    exit_chatroom = ExitChatroom().Field()
    edit_profile = EditProfile().Field()
    uploads = UploadsMutation().Field()

schema = graphene.Schema(query=Query, mutation=Mutation)
