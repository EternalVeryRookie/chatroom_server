from django.core.validators import EmailValidator
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, UserManager, PermissionsMixin
from django.contrib.auth.validators import UnicodeUsernameValidator, ASCIIUsernameValidator
from django.http.request import HttpRequest
from django.utils import timezone


class UserName(models.Model):
    username = models.CharField(
        max_length=150,
        validators=[UnicodeUsernameValidator(message="ユーザー名に使用できるの記号は@/./+/-/_のみです")],
        unique=True,
        error_messages={
            "unique": "そのユーザー名は既に使用されています",
            "max_length": "ユーザー名の文字数の上限は150です"
        }
    )

    def __str__(self):
        return self.username
    
    @property
    def user(self):
        if hasattr(self, "userongoogle"):
            return self.userongoogle
        elif hasattr(self, "useronmyapp"):
            return self.useronmyapp

        return None
        

    @property
    def email(self):
        user = self.user
        if user:
            return user.email
            
        return ""


class CustomUserManager(UserManager):
    use_in_migrations = True

    def _create_user(self, username, email, password, **extra_fields):
        """
        Create and save a user with the given username, email, and password.
        """
        if not username:
            raise ValueError('The given username must be set')
        email = self.normalize_email(email)
        username = self.model.normalize_username(username)
        username = UserName(username=username)
        username.full_clean()
        username.save()
        try:
            user = self.model(username=username, email=email, **extra_fields)
            user.set_password(password)
            user.save(using=self._db)
            return user
        except:
            username.delete()
            raise

    def create_user(self, username, email=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(username, email, password, **extra_fields)

    def create_superuser(self, username=None, email=None, password=None, **extra_fields):
        if username is None:
            username = "root"

        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(username, email, password, **extra_fields)


class UserOnMyApp(AbstractBaseUser, PermissionsMixin):
    username = models.OneToOneField(
        UserName,
        on_delete=models.CASCADE
    )

    email = models.CharField(
        unique=True,
        blank=False,
        max_length=300,
        error_messages={
            "unique": "そのメールアドレスは既に使用されています"
        },
        validators=[EmailValidator("メールアドレスの形式が不正です")]
    )
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(('date joined'), default=timezone.now)

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS=[]

    @property
    def name(self):
        return self.username


class UserOnGoogle(models.Model):
    #id tokenのsub属性を利用する。Googleのサービスで一意の識別子で変更されない
    #参考　https://developers.google.com/identity/protocols/oauth2/openid-connect#createxsrftoken
    id = models.CharField(
        "Google ID",
        max_length=255,
        validators=[ASCIIUsernameValidator()],
        primary_key=True
    )

    email = models.CharField(
        unique=True,
        blank=False,
        max_length=300,
        error_messages={
            "unique": "そのメールアドレスは既に使用されています"
        },
        validators=[EmailValidator("メールアドレスの形式が不正です")]
    )

    username = models.OneToOneField(
        UserName,
        on_delete=models.CASCADE
    )
    
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    date_joined = models.DateTimeField(('date joined'), default=timezone.now)
    last_login = models.DateTimeField(('last login'), blank=True, null=True)


    @property
    def name(self):
        return self.username