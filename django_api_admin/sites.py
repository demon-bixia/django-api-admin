import re

from django.contrib.admin import ModelAdmin, AdminSite
from django_api_admin import views as api_views
from django.core.exceptions import ImproperlyConfigured
from django.db.models.base import ModelBase
from django.urls import path, include


class AlreadyRegistered(Exception):
    pass


class NotRegistered(Exception):
    pass


class APIAdminSite(AdminSite):
    """
    Encapsulates an instance of the django admin application.

    todo override register() to register a custom model admin
    todo override get_urls() to replace permissions with custom ones
    """

    def __init__(self, default_admin_class=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.default_admin_class = default_admin_class or ModelAdmin

    def login(self, request, extra_context=None):
        return api_views.LoginView.as_view()(request, extra_context)

    def logout(self, request, extra_context=None):
        return api_views.LogoutView.as_view()(request, extra_context)

    def password_change(self, request, extra_context=None):
        return api_views.PasswordChangeView.as_view()(request, extra_context)

    def index(self, request, extra_context=None):
        return api_views.IndexView.as_view()(request, self, extra_context)

    def app_index(self, request, app_label, extra_context=None):
        return api_views.AppIndexView.as_view()(request, self, app_label, extra_context)


site = APIAdminSite()
