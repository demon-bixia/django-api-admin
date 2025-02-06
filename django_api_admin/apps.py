from django.apps import AppConfig
from django.core import checks
from django.utils.translation import gettext_lazy as _

from django_api_admin.checks import check_admin_app, check_dependencies


class DjangoApiAdminConfig(AppConfig):
    """Simple AppConfig which does not do automatic discovery."""
    default_auto_field = 'django.db.models.BigAutoField'
    default_site = "django_api_admin.sites.APIAdminSite"
    name = 'django_api_admin'
    verbose_name = _("Administration")

    def ready(self):
        checks.register(check_dependencies, checks.Tags.admin)
        checks.register(check_admin_app, checks.Tags.admin)


class DjangoApiAdminConfig(DjangoApiAdminConfig):
    """The default AppConfig for admin which does autodiscovery."""

    default = True

    def ready(self):
        super().ready()
        self.module.autodiscover()
