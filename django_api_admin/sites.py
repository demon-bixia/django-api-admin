from functools import update_wrapper

from django.apps import apps
from django.contrib.admin import ModelAdmin, AdminSite
from django.urls import NoReverseMatch
from django.urls import reverse
from django.utils.text import capfirst
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect

from django_api_admin import views as api_views
from django_api_admin.permissions import IsAdminUser
from django_api_admin.serializers import PasswordChangeSerializer, LoginSerializer, UserSerializer


class APIAdminSite(AdminSite):
    """
    Encapsulates an instance of the django admin application.

    todo override register() to register a custom model admin.
    """
    default_admin_class = None
    # optional views
    include_view_on_site_view = False
    include_root_view = True
    include_final_catch_all_view = False
    # default permissions
    default_permission_classes = [IsAdminUser, ]
    # default serializers
    login_serializer = LoginSerializer
    password_change_serializer = PasswordChangeSerializer
    user_serializer = UserSerializer

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)
        self.default_admin_class = self.default_admin_class or ModelAdmin

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
                        f'{self.name}:app_list',
                        kwargs={'app_label': app_label},
                        current_app=self.name,
                    ),
                    'has_module_perms': has_module_perms,
                    'models': [model_dict],
                }

        if label:
            return app_dict.get(label)
        return app_dict

    def api_admin_view(self, view, cacheable=False):
        """
        Adds caching, csrf protection and drf api_specific attributes
        """

        def inner(request, *args, **kwargs):
            return view(request, *args, **kwargs)

        if not cacheable:
            inner = never_cache(inner)

        if not getattr(inner, 'csrf_exempt', False):
            inner = csrf_protect(inner)

        return update_wrapper(inner, view)

    # todo refactor to add model_admin urls
    def get_urls(self):
        from django.urls import path, re_path
        from django.contrib.contenttypes import views as contenttype_views

        urlpatterns = [
            path('index/', self.api_admin_view(self.index), name='index'),
            path('login/', self.api_admin_view(self.login), name='login'),
            path('logout/', self.api_admin_view(self.logout), name='logout'),
            path('password_change/', self.api_admin_view(self.password_change, cacheable=True), name='password_change'),
            path('autocomplete/', self.api_admin_view(self.autocomplete_view), name='autocomplete'),
            path('jsi18n/', self.api_admin_view(self.i18n_javascript, cacheable=True), name='language_catalog'),
        ]

        # add the app detail view
        valid_app_labels = [model._meta.app_label for model, model_admin in self._registry.items()]
        regex = r'^(?P<app_label>' + '|'.join(valid_app_labels) + ')/$'
        urlpatterns.append(re_path(regex, self.api_admin_view(self.app_index), name='app_list'))

        # add optional views
        if self.include_view_on_site_view:
            urlpatterns.append(path(
                'r/<int:content_type_id>/<path:object_id>/',
                contenttype_views.shortcut,
                name='view_on_site',
            ))

        if self.include_root_view:
            # remove detail, redirect urls and urls with no names
            excluded_url_names = ['app_list', 'view_on_site']
            root_urls = [url for url in urlpatterns if url.name and url.name not in excluded_url_names]
            root_view = api_views.AdminAPIRootView.as_view(root_urls=root_urls)
            urlpatterns.append(path('', root_view, name='api-root'))

        if self.include_final_catch_all_view:
            urlpatterns.append(re_path(r'(?P<url>.*)$', self.catch_all_view, name='final_catch_all'))

        return urlpatterns

    @property
    def urls(self):
        return self.get_urls(), self.name, self.name

    def index(self, request, extra_context=None):
        defaults = {
            'permission_classes': self.default_permission_classes,
        }

        return api_views.IndexView.as_view(**defaults)(request, admin_site=self)

    def app_index(self, request, app_label, extra_context=None):
        defaults = {
            'permission_classes': self.default_permission_classes,
        }
        return api_views.AppIndexView.as_view(**defaults)(request, app_label=app_label, admin_site=self)

    def login(self, request, extra_context=None):
        defaults = {
            'permission_classes': self.default_permission_classes,
            'serializer_class': self.login_serializer,
            'user_serializer_class': self.user_serializer,
        }

        return api_views.LoginView.as_view(**defaults)(request)

    def logout(self, request, extra_context=None):
        defaults = {
            'permission_classes': self.default_permission_classes,
            'user_serializer_class': self.user_serializer,
        }

        return api_views.LogoutView.as_view(**defaults)(request)

    def password_change(self, request, extra_context=None):
        defaults = {
            'permission_classes': self.default_permission_classes,
            'serializer_class': self.password_change_serializer,
        }
        return api_views.PasswordChangeView.as_view(**defaults)(request)

    def i18n_javascript(self, request, extra_context=None):
        defaults = {
            'permission_classes': self.default_permission_classes,
        }
        return api_views.LanguageCatalogView.as_view(**defaults)(request)

    def autocomplete_view(self, request):
        defaults = {
            'permission_classes': self.default_permission_classes,
        }
        return api_views.AutoCompleteView.as_view(**defaults)(request, admin_site=self)


site = APIAdminSite(name='api_admin')
