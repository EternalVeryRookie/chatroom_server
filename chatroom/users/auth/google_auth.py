import pathlib
import json
import base64
from typing import NoReturn

import google_auth_oauthlib.flow
from django.http.request import HttpRequest



# Googleの名前があるのでこれは外側の層。内側にSSOモジュールを追加するのがよさそう。
class GoogleAuth:
    def __init__(self) -> None:
        self.__cred_filepath = pathlib.Path(__file__).parent / "google_client_secret.json"


    def create_auth_url(self):
        flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
            str(self.__cred_filepath),
            scopes=["openid", "https://www.googleapis.com/auth/userinfo.email"]
        )
        flow.redirect_uri = "https://localhost:8000/users/googleauthcallback"

        auth_url, state = flow.authorization_url(access_type="offline", include_granted_scopes="true")
        return auth_url, state


    def authentication(self, auth_code, generated_state, request_state, session):
        """
        リダイレクト後に呼ばれる
        """
        if generated_state != request_state:
            return None, None, None

        flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
            str(self.__cred_filepath),
            scopes=["openid", "https://www.googleapis.com/auth/userinfo.email"],
            state=request_state
        )
        flow.redirect_uri = "https://localhost:8000/users/googleauthcallback"
        flow.fetch_token(code=auth_code)
        id_token = flow.credentials.id_token
        claim = id_token.split(".")
        # 以下はbinascii.Error: Incorrect padding対策
        jwt_b64 = claim[1] + ('=' * (-len(claim[1]) % 4))
        payload = json.loads(base64.b64decode(jwt_b64).decode())
        username = payload["email"].split("@")[0]
        session["google-user"] = {
            "id": payload["sub"]
        }
        
        return username, payload["sub"], payload["email"]
        

    def sign_out(self, request:HttpRequest)->NoReturn:
        if self.is_sign_in(request):
            del request.session["google-user"]


    def user_id(self, request:HttpRequest)->str:
        if self.is_sign_in(request):
            return request.session["google-user"]["id"]

        return None

    def is_sign_in(self, request:HttpRequest)->bool:
        return "google-auth" in request.session

