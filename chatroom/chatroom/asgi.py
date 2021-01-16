"""
ASGI config for chatroom project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.1/howto/deployment/asgi/
"""

import os

from django.urls import re_path
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from users.auth.google_auth_consumer import GoogleAuthConsumer

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatroom.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    # Just HTTP for now. (We can add other protocols later.)
    "websocket": AuthMiddlewareStack(
        URLRouter([
            re_path(r"^oauthcallback/(?P<state>\w+)/$", GoogleAuthConsumer.as_asgi())
        ])
    )
})