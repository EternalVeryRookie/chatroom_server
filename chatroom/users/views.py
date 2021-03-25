from typing import Final
import traceback

from django.http.request import HttpRequest
from django.http.response import HttpResponse, HttpResponseRedirect, JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET

from users.models import UserOnGoogle, UserName

from .auth.google_auth import GoogleAuth
from .auth.auth import Auth


OAUTH_REDIRECT_URL: Final[str] = "https://localhost:8000"

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
        username, user_id, email = GoogleAuth(request).authentication(code, generated_state, request.GET.get(key="state", default=""), request.session)
        if username is None:
            return JsonResponse({"isok": False, "errors": [{"message": "authentication failed", "error_type": "auth error"}]})

        if UserOnGoogle.objects.filter(pk=user_id).exists():
            user = UserOnGoogle.objects.get(id=user_id)
        else:
            user = UserOnGoogle.objects.create(username=username, id=user_id, email=email)
            user.last_login = timezone.now()
            user.save()
            
    except Exception as e:
        traceback.print_stack()
        return JsonResponse({"isok": False, "errors": [{"message": "authentication failed", "error_type": "auth error"}]})

    return HttpResponseRedirect(OAUTH_REDIRECT_URL)