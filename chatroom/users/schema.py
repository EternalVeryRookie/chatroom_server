from django.contrib.sessions.backends.base import SessionBase
from django.core.exceptions import ValidationError
from .models import UserName, UserOnGoogle
from django.db.utils import IntegrityError
from graphene_django import DjangoObjectType
from graphene_django.filter import DjangoFilterConnectionField
import graphene
from graphene import relay

from .repository import MyAppUserRepository
from .auth.my_app_auth import MyAppAuth
from .auth.auth import Auth
from .auth.google_auth import GoogleAuth

import json


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


class Error(graphene.ObjectType):
    message = graphene.String()
    error_type = graphene.String()


class SignUp(graphene.Mutation):
    class Arguments:
        username = graphene.String()
        password = graphene.String()
        email = graphene.String()

    ok = graphene.Boolean()
    errors = graphene.List(Error)
    user = graphene.Field(UserNameNode)

    @classmethod
    def mutate(cls, root, info, username, password, email):
        try:
            user = MyAppUserRepository().create(username, password, email)
            MyAppAuth(info.context).sign_out()
            user = MyAppAuth(info.context).sign_in(email, password)
            return SignUp(ok=True, errors=None, user=user.username)
        except ValidationError as validation_error:
            messages = json.loads(str(validation_error).replace("'", '"'))
            errors = []
            for key in messages:
                for msg in messages[key]:
                    errors.append(Error(message=msg, error_type=key))

            return SignUp(ok=False, errors=errors, user=None)
        except IntegrityError as error:
            errors = [Error(message=str(error), error_type="server error")]

            return SignUp(ok=False, errors=errors, user=None)


class SignIn(graphene.Mutation):
    class Arguments:
        email = graphene.String()
        password = graphene.String()

    ok = graphene.Boolean()
    errors = graphene.List(Error)
    user = graphene.Field(UserNameNode)

    @classmethod
    def mutate(cls, root, info, email, password):
        Auth(info.context).sign_out()
        user = MyAppAuth(info.context).sign_in(email, password)
        if user is None:
            err = Error(message="メールアドレスまたはパスワードが異なっています", error_type="not auth")
            return SignIn(ok=False, errors=[err], user=None)


        return SignIn(ok=True, errors=None, user=user.username)


class SignOut(graphene.Mutation):
    class Arguments:
        pass

    ok = graphene.Boolean()

    @classmethod
    def mutate(cls, root, info):
        Auth(info.context).sign_out()

        return SignOut(ok=True)


class SingleSignOn(graphene.Mutation):
    class Arguments:
        provider = graphene.String()

    ok = graphene.Boolean()
    errors = graphene.List(Error)
    redirect_url = graphene.String()

    @classmethod
    def mutate(cls, root, info, provider):
        if provider != "google":
            return SingleSignOn(ok=False, errors=[Error(message="%s認証はサポートしていません" % provider, error_type="not support auth provider")])
        
        auth_url, state = GoogleAuth(info.context).create_auth_url()
        info.context.session["state"] = state
        return SingleSignOn(ok=True, errors=None, redirect_url=auth_url)


class Mutation(graphene.ObjectType):
    sign_up = SignUp.Field()
    sign_in = SignIn.Field()
    sign_out = SignOut.Field()
    single_sign_on = SingleSignOn.Field()


schema = graphene.Schema(query=Query, mutation=Mutation)

