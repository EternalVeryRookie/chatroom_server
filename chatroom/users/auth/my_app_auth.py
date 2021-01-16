
from typing import NoReturn
from django.http.request import HttpRequest
from django.contrib.auth import logout, authenticate


class MyAppAuth:
    def __init__(self) -> None:
        pass


    def sign_in(self, request, email, password):
        return authenticate(request, username=email, password=password)


    def user_id(self, request:HttpRequest)->str:
        if not self.is_sign_in(request):
            return None

        return request.user.id


    def sign_out(self, request:HttpRequest)->NoReturn:
        logout(request)


    def is_sign_in(self, request:HttpRequest)->bool:
        return request.user.is_authenticated
