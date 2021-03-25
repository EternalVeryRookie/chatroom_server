# Generated by Django 3.1.4 on 2021-03-12 07:46

from django.db import migrations, models
import django.db.models.deletion
import common.validators.image


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_auto_20210304_1243'),
    ]

    operations = [
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('self_introduction', models.CharField(blank=True, max_length=256)),
                ('icon', models.ImageField(default='uploads/DefaultIconImage.png', upload_to='uploads/', validators=[common.validators.image.MaxFileSizeValidator(52428800), common.validators.image.ImageAspectRatioValidator(common.validators.image.WidthHeight(1, 1))])),
                ('cover_image', models.ImageField(default='uploads/DefaultCoverImage.png', upload_to='uploads/', validators=[common.validators.image.MaxFileSizeValidator(52428800), common.validators.image.ImageAspectRatioValidator(common.validators.image.WidthHeight(height=1, width=3))])),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='users.username')),
            ],
        ),
    ]