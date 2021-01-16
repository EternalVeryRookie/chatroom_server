from typing import NoReturn

from django.http.request import HttpRequest

from .google_auth import GoogleAuth
from .my_app_auth import MyAppAuth


class Auth:
    def __init__(self, request:HttpRequest) -> None:
        self.__request = request

    
    @property
    def is_sign_in(self)->bool:
        if MyAppAuth().is_sign_in(self.__request):
            return True

        if GoogleAuth().is_sign_in(self.__request):
            return True

        return False


    def sign_out(self)->NoReturn:
        GoogleAuth().sign_out(self.__request)
        MyAppAuth().sign_out(self.__request)

