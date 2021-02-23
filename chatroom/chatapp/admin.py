from django.contrib import admin
from django.contrib.auth.hashers import make_password

from users.models import UserName
from .models import ChatroomMember, Chatroom, ChatMessage, PrivateChatroom, PrivateChatMessage, PrivateChatroomMember, UserProfile

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "self_introduction", "icon", "cover_image")

@admin.register(Chatroom)
class ChatroomAdmin(admin.ModelAdmin):
    list_display = ("room_name", "is_active", "create_user", "create_date")
    
@admin.register(PrivateChatroom)
class PrivateChatroomAdmin(admin.ModelAdmin):
    list_display = ("room_name", "is_active", "create_user", "create_date")

    def save_model(self, request, obj, form, change):
        create_user = UserName.objects.get(pk=request.POST["create_user"])
        name = request.POST["room_name"]

        PrivateChatroom.create(name=name, create_user=create_user)

@admin.register(ChatroomMember)
@admin.register(PrivateChatroomMember)
class ChatroomMemberAdmin(admin.ModelAdmin):
    list_display = ("room", "user", "role", "is_enter")

@admin.register(ChatMessage)
@admin.register(PrivateChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("sender", "room")