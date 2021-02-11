from typing import NoReturn

from django.http.request import HttpRequest

from .google_auth import GoogleAuth
from .my_app_auth import MyAppAuth
from ..models import UserName


class Auth:
    def __init__(self, request:HttpRequest) -> None:
        self.__request = request

    
    @property
    def is_sign_in(self)->bool:
        if MyAppAuth(self.__request).is_sign_in:
            return True

        if GoogleAuth(self.__request).is_sign_in:
            return True

        return False


    def sign_out(self)->NoReturn:
        GoogleAuth(self.__request).sign_out()
        MyAppAuth(self.__request).sign_out()

    
    def is_same_user(self, username:UserName) -> bool:
        if hasattr(username, "userongoogle"):
            return GoogleAuth(self.__request).user_id == username.userongoogle.id
        elif hasattr(username, "useronmyapp"):
            return MyAppAuth(self.__request).user_id == username.useronmyapp.id

        return False


    @property
    def current_user(self)->UserName:
        auth = MyAppAuth(self.__request)
        if auth.is_sign_in:
            return auth.current_user.username
        
        auth = GoogleAuth(self.__request)
        if auth.is_sign_in:
            return auth.current_user.username

        return None