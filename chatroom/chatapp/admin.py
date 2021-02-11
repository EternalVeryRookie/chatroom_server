from django.contrib import admin
from .models import ChatroomMember, Chatroom, ChatMessage

@admin.register(ChatroomMember, Chatroom, ChatMessage)
class ChatAppAdmin(admin.ModelAdmin):
    pass