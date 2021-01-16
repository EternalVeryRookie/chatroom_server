from .models import UserName,UserOnGoogle
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model


class FailedAssignSequentialNumber(Exception):
    pass


class UserNameRepository:
    def __init__(self) -> None:
        pass


    def create_assign_sequential_number(self, username):
        """
        与えられたusernameに対して連番を付与することでユーザー名の重複をなくす
        重複をなくした上でユーザー名を登録する
        """

        for i in range(200000):
            tmp_name = username
            try:
                name = UserName(username=get_user_model().normalize_username(tmp_name))
                name.full_clean()
                name.save()
                return name
            except ValidationError:
                tmp_name = username + str(i)
                i+=1

        raise FailedAssignSequentialNumber("連番の付与に失敗しました。ユーザー名%sは使用されすぎています" % username)


    def create(self, username):
        """
        ユーザー名を登録する。ユーザー名の重複は許されていない。
        """
        name = UserName(username=get_user_model().normalize_username(username))
        name.full_clean()
        name.save()
        return name


class GoogleUserRepository:
    def __init__(self) -> None:
        pass


    def create(self, username, sub, email)->UserOnGoogle:
        """
        Googleアカウントユーザーを作成する
        """
        user = self.find(sub)
        if user:
            return user

        username = UserNameRepository().create_assign_sequential_number(username)
        user = UserOnGoogle.objects.create(id=sub, email=email, username=username)
        return user


    def find(self, user_id)->UserOnGoogle:
        """
        指定のidを持つGoogleユーザーを検索する
        """
        try:
            return UserOnGoogle.objects.get(id=user_id)
        except UserOnGoogle.DoesNotExist:
            return None


class MyAppUserRepository:
    def __init__(self) -> None:
        super().__init__()


    def create(self, username, password, email):
        user = get_user_model().objects.create_user(username=username, password=password, email=email)
        return user