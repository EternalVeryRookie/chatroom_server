from django.core.exceptions import ValidationError
from .models import UserName
from graphql_relay import from_global_id
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
import graphene
from graphene import relay

from .repository import MyAppUserRepository
from .auth.my_app_auth import MyAppAuth
from .auth.auth import Auth
from .auth.google_auth import GoogleAuth
from errors.graphql_error_decorator import reraise_graphql_error


class UserNameNode(DjangoObjectType):
    class Meta:
        model = UserName
        filter_fields  = ["id", "username", ]
        interfaces = (relay.Node, )


    email = graphene.String()


    def resolve_email(self, info):
        if Auth(info.context).is_same_user(self):
            return self.email

        return ""


class Query(graphene.ObjectType):
    user = relay.Node.Field(UserNameNode)
    current_user = graphene.Field(UserNameNode)
    user_by_name = graphene.Field(UserNameNode, username=graphene.String(required=True))
    all_user = DjangoFilterConnectionField(UserNameNode)


    def resolve_user_by_name(root, info, username):
        try:
            return UserName.objects.get(username=username)
        except UserName.DoesNotExist:
            return None


    def resolve_current_user(root, info):
        return Auth(info.context).current_user


    def resolve_all_user(root, info):
        return UserName.objects.all()


class SignUp(graphene.Mutation):
    class Arguments:
        username = graphene.String()
        password = graphene.String()
        email = graphene.String()

    ok = graphene.Boolean()
    user = graphene.Field(UserNameNode)

    @reraise_graphql_error
    @classmethod
    def mutate(cls, root, info, username, password, email):
        user = MyAppUserRepository().create(username, password, email)
        MyAppAuth(info.context).sign_out()
        user = MyAppAuth(info.context).sign_in(email, password)
        return SignUp(ok=True, errors=None, user=user.username)


class SignIn(graphene.Mutation):
    class Arguments:
        email = graphene.String()
        password = graphene.String()

    ok = graphene.Boolean()
    user = graphene.Field(UserNameNode)

    @reraise_graphql_error
    @classmethod
    def mutate(cls, root, info, email, password):
        Auth(info.context).sign_out()
        user = MyAppAuth(info.context).sign_in(email, password)
        if user is None:
            raise Exception("メールアドレスまたはパスワードが異なっています")

        return SignIn(ok=True, errors=None, user=user.username)


class SignOut(graphene.Mutation):
    class Arguments:
        pass

    ok = graphene.Boolean()

    @reraise_graphql_error
    @classmethod
    def mutate(cls, root, info):
        Auth(info.context).sign_out()

        return SignOut(ok=True)


class SingleSignOn(graphene.Mutation):
    class Arguments:
        provider = graphene.String()

    ok = graphene.Boolean()
    redirect_url = graphene.String()

    @reraise_graphql_error
    @classmethod
    def mutate(cls, root, info, provider):
        if provider != "google":
            raise Exception(f"{provider}認証はサポートしていません")
        
        auth_url, state = GoogleAuth(info.context).create_auth_url()
        info.context.session["state"] = state
        return SingleSignOn(ok=True, errors=None, redirect_url=auth_url)


class RenameUserName(relay.ClientIDMutation):
    class Input:
        new_name = graphene.String()
        id = graphene.ID()

    ok = graphene.Boolean()
    user_name = graphene.Field(UserNameNode)

    @reraise_graphql_error
    @classmethod
    def mutate_and_get_payload(cls, root, info, new_name, id):
        try:
            nod_type, primary_id = from_global_id(id)
        except UnicodeDecodeError as ude:
            raise Exception(f"id「{id}」のユーザーが見つかりませんでした") from ude

        if nod_type != "UserNameNode":
            raise Exception(f"id「{id}」のユーザーが見つかりませんでした")

        try:
            username: UserName = UserName.objects.get(pk=primary_id)
        except UserName.DoesNotExist as dne:
            raise Exception(f"id「{id}」のユーザーが見つかりませんでした") from dne

        username.username = new_name
        username.full_clean()
        username.save()

        return RenameUserName(ok=True, user_name=username)


class Mutation(graphene.ObjectType):
    sign_up = SignUp.Field()
    sign_in = SignIn.Field()
    sign_out = SignOut.Field()
    single_sign_on = SingleSignOn.Field()
    rename_user_name = RenameUserName.Field()


schema = graphene.Schema(query=Query, mutation=Mutation)
