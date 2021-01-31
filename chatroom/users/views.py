from typing import Final
from django.http.request import HttpRequest
from django.http.response import HttpResponse, HttpResponseRedirect, JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET

from .repository import GoogleUserRepository
from .auth.google_auth import GoogleAuth
from .auth.auth import Auth


OAUTH_REDIRECT_URL: Final[str] = "http://127.0.0.1:8080"

@require_GET
def google_auth_callback(request:HttpRequest) -> HttpResponse:
    code = request.GET.get(key="code", default="")
    if code == "":
        err = request.GET.get(key="error")
        return JsonResponse({"error": err})

    generated_state = ""
    if "state" in request.session:
        generated_state = request.session["state"]
 
    try:
        Auth(request).sign_out()
        username, user_id, email = GoogleAuth().authentication(code, generated_state, request.GET.get(key="state", default=""), request.session)
        if username is None:
            return JsonResponse({"isok": False, "errors": [{"message": "authentication failed", "error_type": "auth error"}]})

        user = GoogleUserRepository().create(username, user_id, email)
        user.last_login = timezone.now()
        user.save()
        request.session.save()
    except Exception as e:
        return JsonResponse({"isok": False, "errors": [{"message": "authentication failed", "error_type": "auth error"}]})

    return HttpResponseRedirect(OAUTH_REDIRECT_URL)