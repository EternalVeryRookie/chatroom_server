# Generated by Django 3.1.4 on 2021-02-14 13:48

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('users', '__first__'),
    ]

    operations = [
        migrations.CreateModel(
            name='Chatroom',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('room_name', models.CharField(max_length=100)),
                ('create_date', models.DateTimeField(auto_now_add=True)),
                ('is_active', models.BooleanField(default=True)),
                ('create_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='users.username')),
            ],
        ),
        migrations.CreateModel(
            name='PrivateChatroom',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('password', models.CharField(max_length=512)),
                ('room_name', models.CharField(max_length=100)),
                ('create_date', models.DateTimeField(auto_now_add=True)),
                ('is_active', models.BooleanField(default=True)),
                ('create_user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='users.username')),
            ],
        ),
        migrations.CreateModel(
            name='ChatroomMember',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('is_enter', models.BooleanField(default=False)),
                ('role', models.CharField(choices=[('GU', 'Guest'), ('MA', 'Manager'), ('OW', 'Owner')], default='GU', max_length=2)),
                ('room', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='chatapp.chatroom')),
                ('user', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='users.username')),
            ],
        ),
        migrations.CreateModel(
            name='ChatMessage',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('send_date', models.DateTimeField(auto_now_add=True)),
                ('text', models.CharField(error_messages={'max_length': 'メッセージの文字数の上限は2048です'}, max_length=2048)),
                ('room', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='chatapp.chatroom')),
                ('sender', models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='users.username')),
            ],
        ),
    ]
