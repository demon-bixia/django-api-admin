from django.apps import AppConfig


class CustomDjangoApiAdminConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'custom_django_api_admin'
