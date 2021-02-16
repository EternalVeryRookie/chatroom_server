import functools

from django.http.request import HttpRequest

from users.auth.auth import Auth

def require_sign_in(f):
    @functools.wraps(f)
    def logic(request:HttpRequest, *args, **kwargs):
        if not  Auth(request).is_sign_in:
            raise Exception("サインインしてください")

        return f(request, *args, **kwargs)

    return logic
