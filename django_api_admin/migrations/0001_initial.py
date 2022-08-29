# Generated by Django 4.1 on 2022-08-29 17:39

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Author',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('age', models.IntegerField(choices=[(60, 'senior'), (1, 'baby'), (2, 'also a baby')])),
                ('is_vip', models.BooleanField(default=False)),
                ('gender', models.CharField(max_length=20)),
                ('date_joined', models.DateTimeField(auto_now_add=True)),
                ('title', models.CharField(max_length=20, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='GuestEntry',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_entered', models.DateField()),
            ],
        ),
        migrations.CreateModel(
            name='Publisher',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='Book',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=100)),
                ('author', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='django_api_admin.author')),
                ('credits', models.ManyToManyField(related_name='credits', to='django_api_admin.author')),
            ],
        ),
        migrations.AddField(
            model_name='author',
            name='publisher',
            field=models.ManyToManyField(to='django_api_admin.publisher'),
        ),
        migrations.AddField(
            model_name='author',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL),
        ),
    ]