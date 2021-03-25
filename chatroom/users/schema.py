import base64
import hashlib

from graphql_relay import from_global_id
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
import graphene
from django.contrib.auth import get_user_model
from django.db.models.fields.files import ImageFieldFile
from graphene_django.fields import DjangoConnectionField
from graphene_file_upload.scalars import Upload
from django.core.files.images import ImageFile

from .models import UserName, UserProfile
from .auth.my_app_auth import MyAppAuth
from .auth.auth import Auth
from .auth.google_auth import GoogleAuth
from common.errors.graphql_error_decorator import reraise_graphql_error
from common.nodes.url_safe_encode_node import UrlSafeEncodeNode


class UserNameNode(DjangoObjectType):
    class Meta:
        model = UserName
        filter_fields  = ["id", "username", ]
        interfaces = (UrlSafeEncodeNode, )

    email = graphene.String()

    def resolve_email(self, info):
        if Auth(info.context).is_same_user(self):
            return self.email

        return ""


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
    user = UrlSafeEncodeNode.Field(UserNameNode)
    current_user = graphene.Field(UserNameNode)
    user_profile = UrlSafeEncodeNode.Field(UserProfileNode)
    user_by_name = graphene.Field(UserNameNode, username=graphene.String(required=True))
    all_user = DjangoFilterConnectionField(UserNameNode)
    all_profiles = DjangoConnectionField(UserProfileNode)
    current_user_profile = graphene.Field(UserProfileNode)
    user_profile_by_user_id = graphene.Field(UserProfileNode, id=graphene.ID())

    def resolve_user_by_name(root, info, username):
        try:
            return UserName.objects.get(username=username)
        except UserName.DoesNotExist:
            return None

    def resolve_current_user(root, info):
        return Auth(info.context).current_user

    def resolve_all_user(root, info):
        return UserName.objects.all()

    def resolve_current_user_profile(root, info):
        current = Auth(info.context).current_user
        try:
            return UserProfile.objects.get(user = current)
        except:
            return UserProfile.objects.create(user=current)

    def resolve_user_profile_by_user_id(root, info, id):
        try:
            node_type, user_pk = from_global_id(id)
        except UnicodeDecodeError:
            raise Exception("指定のユーザーは存在しません")
    
        if node_type != str(UserNameNode):
            raise Exception("指定のユーザーは存在しません")

        try:
            return UserProfile.objects.get(user__pk=user_pk)
        except UserProfile.DoesNotExist:
            return UserProfile.objects.create(user=UserName.objects.get(pk=user_pk))


class SignUp(graphene.Mutation):
    class Arguments:
        username = graphene.String()
        password = graphene.String()
        email = graphene.String()

    ok = graphene.Boolean()
    user = graphene.Field(UserNameNode)

    @classmethod
    @reraise_graphql_error
    def mutate(cls, root, info, username, password, email):
        get_user_model().objects.create_user(username=username, password=password, email=email)
        MyAppAuth(info.context).sign_out()
        user = MyAppAuth(info.context).sign_in(email, password)
        return SignUp(ok=True, user=user.username)


class SignIn(graphene.Mutation):
    class Arguments:
        email = graphene.String()
        password = graphene.String()

    ok = graphene.Boolean()
    user = graphene.Field(UserNameNode)

    @classmethod
    @reraise_graphql_error
    def mutate(cls, root, info, email, password):
        Auth(info.context).sign_out()
        user = MyAppAuth(info.context).sign_in(email, password)
        if user is None:
            raise Exception("メールアドレスまたはパスワードが異なっています")

        return SignIn(ok=True, user=user.username)


class SignOut(graphene.Mutation):
    class Arguments:
        pass

    ok = graphene.Boolean()

    @classmethod
    @reraise_graphql_error
    def mutate(cls, root, info):
        Auth(info.context).sign_out()

        return SignOut(ok=True)


class SingleSignOn(graphene.Mutation):
    class Arguments:
        provider = graphene.String()

    ok = graphene.Boolean()
    redirect_url = graphene.String()

    @classmethod
    @reraise_graphql_error
    def mutate(cls, root, info, provider):
        if provider != "google":
            raise Exception(f"{provider}認証はサポートしていません")
        
        auth_url, state = GoogleAuth(info.context).create_auth_url()
        info.context.session["state"] = state
        return SingleSignOn(ok=True, redirect_url=auth_url)


class RenameUserName(graphene.Mutation):
    class Arguments:
        new_name = graphene.String()
        id = graphene.ID()

    ok = graphene.Boolean()
    user_name = graphene.Field(UserNameNode)

    @classmethod
    @reraise_graphql_error
    def mutate(cls, root, info, new_name, id):
        try:
            nod_type, primary_id = from_global_id(id)
        except UnicodeDecodeError as ude:
            raise Exception(f"id「{id}」のユーザーが見つかりませんでした") from ude

        if nod_type != str(UserNameNode):
            raise Exception(f"id「{id}」のユーザーが見つかりませんでした")

        try:
            username: UserName = UserName.objects.get(pk=primary_id)
        except UserName.DoesNotExist as dne:
            raise Exception(f"id「{id}」のユーザーが見つかりませんでした") from dne

        username.username = new_name
        username.full_clean()
        username.save()

        return RenameUserName(ok=True, user_name=username)


class EditProfile(graphene.Mutation):
    class Arguments:
        user_name = graphene.String(required=False)
        self_introduction = graphene.String(required=False)
        icon = Upload(required=False)
        cover_image = Upload(required=False)

    ok = graphene.Boolean()

    def mutate(self, info, **kwargs):
        user = Auth(info.context).current_user
        try:
            profile: UserProfile = UserProfile.objects.get(user=user)
            oldIconPath, oldCoverImagePath = None, None
            if "self_introduction" in kwargs:
                profile.self_introduction = kwargs["self_introduction"]
                
            if "user_name" in kwargs:
                profile.user.username = kwargs["user_name"]
                profile.user.full_clean()
                profile.user.save()

            def save_filename(name, content_type):
                names = name.split(".")
                if len(names) > 1:
                    return hashlib.md5(names[0].encode()).hexdigest() + "." + names[len(names)-1]

                names = content_type.split("/")
                if len(names) > 1:
                    return hashlib.md5(name.encode()).hexdigest() + "." + names[1]

            if "icon" in kwargs:
                oldIconPath = profile.icon.name
                name = save_filename(kwargs["icon"].name, kwargs["icon"].content_type)
                profile.icon = ImageFile(name=name, file=kwargs["icon"])

            if "cover_image" in kwargs:
                oldCoverImagePath = profile.cover_image.name
                name = save_filename(kwargs["cover_image"].name, kwargs["cover_image"].content_type)
                profile.cover_image = ImageFile(name=name, file=kwargs["cover_image"])
            
            profile.full_clean()
            profile.save()
            if oldCoverImagePath and oldCoverImagePath != UserProfile.DEFAULT_COVER_IMAGE_NAME:
                profile.icon.storage.delete(oldCoverImagePath)

            if oldIconPath and oldIconPath != UserProfile.DEFAULT_ICON_NAME:
                profile.icon.storage.delete(oldIconPath)

        except UserProfile.DoesNotExist:
            profile = UserProfile(
                user=user, 
                self_introduction=kwargs.get("self_introduction", ""), 
                icon=kwargs.get("icon", None), 
                cover_image=kwargs.get("cover_image", None), 
            )

            if "user_name" in kwargs:
                profile.user.username = kwargs["user_name"]
                profile.user.full_clean()
                profile.user.save()

            if profile.icon:
                names = profile.icon.name.split(".")
                profile.icon.name = hashlib.md5(names[0].encode()).hexdigest() + "." + names[len(names)-1]

            if profile.cover_image:
                names = profile.cover_image.name.split(".")
                profile.cover_image.name = hashlib.md5(names[0].encode()).hexdigest() + "." + names[len(names)-1]

            profile.full_clean()
            profile.save() 

        return EditProfile(ok=True)



class Mutation(graphene.ObjectType):
    sign_up = SignUp.Field()
    sign_in = SignIn.Field()
    sign_out = SignOut.Field()
    single_sign_on = SingleSignOn.Field()
    rename_user_name = RenameUserName.Field()
    edit_profile = EditProfile.Field()


schema = graphene.Schema(query=Query, mutation=Mutation)
