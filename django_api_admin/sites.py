from django.apps import apps
from django.contrib.admin import ModelAdmin, AdminSite
from django.urls import NoReverseMatch
from django.urls import reverse
from django.utils.text import capfirst
from django_api_admin.views import AdminSiteViewSet
from django_api_admin.routers import AdminRouter


class APIAdminSite(AdminSite):
    """
    Encapsulates an instance of the django admin application.

    todo override register() to register a custom model admin.
    """
    default_admin_class = None
    viewset_class = None
    router_class = None

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)
        self.default_admin_class = self.default_admin_class or ModelAdmin
        self.viewset_class = self.viewset_class or AdminSiteViewSet
        self.router_class = self.router_class or AdminRouter

    # todo remove admin namespace
    def _build_app_dict(self, request, label=None):
        """
        Build the app dictionary. The optional `label` parameter filters models
        of a specific app.
        """
        app_dict = {}

        if label:
            models = {
                m: m_a for m, m_a in self._registry.items()
                if m._meta.app_label == label
            }
        else:
            models = self._registry

        for model, model_admin in models.items():
            app_label = model._meta.app_label

            has_module_perms = model_admin.has_module_permission(request)
            if not has_module_perms:
                continue

            perms = model_admin.get_model_perms(request)

            # Check whether user has any perm for this module.
            # If so, add the module to the model_list.
            if True not in perms.values():
                continue

            info = (app_label, model._meta.model_name)
            model_dict = {
                'name': capfirst(model._meta.verbose_name_plural),
                'object_name': model._meta.object_name,
                'perms': perms,
                'admin_url': None,
                'add_url': None,
            }
            if perms.get('change') or perms.get('view'):
                model_dict['view_only'] = not perms.get('change')
                try:
                    model_dict['admin_url'] = reverse('admin:%s_%s_changelist' % info, current_app=self.name)
                except NoReverseMatch:
                    pass
            if perms.get('add'):
                try:
                    model_dict['add_url'] = reverse('admin:%s_%s_add' % info, current_app=self.name)
                except NoReverseMatch:
                    pass

            if app_label in app_dict:
                app_dict[app_label]['models'].append(model_dict)
            else:
                app_dict[app_label] = {
                    'name': apps.get_app_config(app_label).verbose_name,
                    'app_label': app_label,
                    'app_url': reverse(
                        'api_admin:app_list',
                        kwargs={'app_label': app_label},
                        current_app=self.name,
                    ),
                    'has_module_perms': has_module_perms,
                    'models': [model_dict],
                }

        if label:
            return app_dict.get(label)
        return app_dict

    # todo refactor to add model_admin urls
    def get_urls(self):
        router = self.router_class(self, trailing_slash=True)
        router.register(self.name, self.viewset_class)
        return router.urls

    @property
    def urls(self):
        return self.get_urls(), self.name, self.name


site = APIAdminSite(name='api_admin')
