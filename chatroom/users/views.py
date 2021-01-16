from django.http.request import HttpRequest
from django.http.response import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.http import require_GET

from .repository import GoogleUserRepository
from .auth.google_auth import GoogleAuth
from .auth.google_auth_consumer import notify_google_auth_result


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
        username, user_id, email = GoogleAuth().authentication(code, generated_state, request.GET.get(key="state", default=""), request.session)
        if username is None:
            return JsonResponse({"isok": False, "errors": [{"message": "authentication failed", "error_type": "auth error"}]})

        user = GoogleUserRepository().create(username, user_id, email)
        user.last_login = timezone.now()
        user.save()
        
        notify_google_auth_result(generated_state)
    except:
        return JsonResponse({"isok": False, "errors": [{"message": "authentication failed", "error_type": "auth error"}]})

    return JsonResponse({"isok": True, "id": user.id})
