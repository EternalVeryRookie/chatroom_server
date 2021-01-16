from django.urls import path

from . import views

urlpatterns = [
    path("googleauthcallback/", views.google_auth_callback)
]