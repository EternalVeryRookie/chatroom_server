from django.contrib import admin
from django.contrib.auth.hashers import make_password
from .models import ChatroomMember, Chatroom, ChatMessage, PrivateChatroom, PrivateChatMessage, PrivateChatroomMember


@admin.register(Chatroom)
class ChatroomAdmin(admin.ModelAdmin):
    list_display = ("room_name", "is_active", "create_user", "create_date")
    
@admin.register(PrivateChatroom)
class PrivateChatroomAdmin(admin.ModelAdmin):
    list_display = ("room_name", "is_active", "create_user", "create_date")

    def save_model(self, request, obj, form, change):
        password = obj.password
        hashed_password = make_password(password)
        obj.password = hashed_password

        obj.save()

@admin.register(ChatroomMember)
@admin.register(PrivateChatroomMember)
class ChatroomMemberAdmin(admin.ModelAdmin):
    list_display = ("room", "user", "role", "is_enter")

@admin.register(ChatMessage)
@admin.register(PrivateChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ("sender", "room")