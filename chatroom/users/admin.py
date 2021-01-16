from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import UserName, UserOnMyApp, UserOnGoogle
# Register your models here.

@admin.register(UserOnMyApp)
@admin.register(UserOnGoogle)
class CustomAdmin(UserAdmin):
    model = UserOnMyApp
    
    fieldsets = (
        (None, {'fields': ('password', )}),
        (('Personal info'), {'fields': ('email',)}),
        (('Permissions'), {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        (('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    list_display = ('username', 'email', 'is_staff')
    search_fields = ('username', 'email')
    filter_horizontal = ()
    list_filter = ()



class ProfileInline(admin.StackedInline):
    model = UserOnMyApp
    max_num = 1
    can_delete = False

class UserNameAdmin(admin.ModelAdmin):
    list_display=("username", "email")
    
    def email(self, obj):
        return obj.email

admin.site.register(UserName, UserNameAdmin)
