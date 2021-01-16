from channels.generic.websocket import WebsocketConsumer
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def notify_google_auth_result(generated_state):
    """
    websocket通信を介してGoogle認証の結果を通知する
    """
    group_name = "google-auth-consumer-%s" % generated_state
    async_to_sync(get_channel_layer().group_send)(group_name, {"type": "oauth.callback", "text": "true"})


class GoogleAuthConsumer(WebsocketConsumer):
    groups = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def connect(self):
        for key in self.scope:
            print(key)

        self.__group_name = "google-auth-consumer-%s" % self.scope["url_route"]["kwargs"]["state"]
        self.accept()
        async_to_sync(self.channel_layer.group_add)(self.__group_name, self.channel_name)


    def disconnect(self, code):
        async_to_sync(self.channel_layer.group_discard)(self.__group_name, self.channel_name)
        return super().disconnect(code)


    def receive(self, text_data, bytes_data):
        return super().receive(text_data=text_data, bytes_data=bytes_data)


    def oauth_callback(self, message):
        self.send(message["text"])
        self.close()