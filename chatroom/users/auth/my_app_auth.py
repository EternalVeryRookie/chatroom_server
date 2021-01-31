
from typing import NoReturn
from django.http.request import HttpRequest
from django.contrib.auth import logout, authenticate, login

from ..models import UserOnMyApp


class MyAppAuth:
    def __init__(self, request:HttpRequest) -> None:
        self.__request = request


    def sign_in(self, email, password):
        user = authenticate(self.__request, username=email, password=password)
        if user:
            login(self.__request, user)
            
        return user


    def sign_out(self)->NoReturn:
        logout(self.__request)


    @property
    def user_id(self)->str:
        if not self.is_sign_in():
            return None

        return self.__request.user.id


    @property
    def current_user(self)->UserOnMyApp:
        return self.__request.user


    @property
    def is_sign_in(self)->bool:
        return self.__request.user.is_authenticated
