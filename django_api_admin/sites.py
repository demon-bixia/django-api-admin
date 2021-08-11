from functools import update_wrapper

from django.apps import apps
from django.contrib.admin import AdminSite
from django.contrib.admin.sites import AlreadyRegistered
from django.core.exceptions import ImproperlyConfigured
from django.db.models.base import ModelBase
from django.urls import NoReverseMatch
from django.urls import reverse
from django.utils.text import capfirst
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect

from . import actions
from . import serializers as api_serializers
from . import views as api_views
from .options import APIModelAdmin
from .pagination import AdminResultsListPagination
from .permissions import IsAdminUser


class APIAdminSite(AdminSite):
    """
    Encapsulates an instance of the django admin application.
    """
    # default model admin class
    admin_class = APIModelAdmin

    # optional views
    include_view_on_site_view = False
    include_root_view = True
    include_final_catch_all_view = False

    # default permissions
    default_permission_classes = [IsAdminUser, ]

    # default serializers
    login_serializer = api_serializers.LoginSerializer
    password_change_serializer = api_serializers.PasswordChangeSerializer
    user_serializer = api_serializers.UserSerializer
    log_entry_serializer = api_serializers.LogEntrySerializer

    # default result pagination style
    default_pagination_class = AdminResultsListPagination

    def __init__(self, *args, **kwargs):

        super().__init__(*args, **kwargs)

        # replace default delete selected with a custom delete_selected action
        self._actions = {'delete_selected': actions.delete_selected}
        self._global_actions = self._actions.copy()
        self.admin_class = self.admin_class or APIModelAdmin

    def register(self, model_or_iterable, admin_class=None, **options):
        admin_class = admin_class or self.admin_class

        if isinstance(model_or_iterable, ModelBase):
            model_or_iterable = [model_or_iterable]

        for model in model_or_iterable:
            if model._meta.abstract:
                raise ImproperlyConfigured(
                    'The model %s is abstract, so it cannot be registered with admin.' % model.__name__
                )

            if model in self._registry:
                raise AlreadyRegistered('The model %s is already registered ' % model.__name__)

            if not model._meta.swapped:
                if options:
                    options['__module__'] = __name__
                    admin_class = type("%sAdmin" % model.__name__, (admin_class,), options)

                # Instantiate the admin class to save in the registry
                self._registry[model] = admin_class(model, self)

    def api_admin_view(self, view, cacheable=False):
        """
        Adds caching, csrf protection and drf api_specific attributes.
        Note: does not add permission checking to views.
        """

        def inner(request, *args, **kwargs):
            return view(request, *args, **kwargs)

        if not cacheable:
            inner = never_cache(inner)

        if not getattr(inner, 'csrf_exempt', False):
            inner = csrf_protect(inner)

        return update_wrapper(inner, view)

    def get_urls(self):
        from django.urls import path, re_path, include, URLPattern
        from django.contrib.contenttypes import views as contenttype_views

        urlpatterns = [
            path('index/', self.api_admin_view(self.index), name='index'),
            path('login/', self.api_admin_view(self.login), name='login'),
            path('logout/', self.api_admin_view(self.logout), name='logout'),
            path('password_change/', self.api_admin_view(self.password_change, cacheable=True), name='password_change'),
            path('autocomplete/', self.api_admin_view(self.autocomplete_view), name='autocomplete'),
            path('jsi18n/', self.api_admin_view(self.i18n_javascript, cacheable=True), name='language_catalog'),
            path('site_context/', self.api_admin_view(self.site_context_view), name='site_context'),
            path('admin_log/', self.api_admin_view(self.admin_log_view), name='admin_log'),
        ]

        # add the app detail view
        valid_app_labels = [model._meta.app_label for model, model_admin in self._registry.items()]
        regex = r'^(?P<app_label>' + '|'.join(valid_app_labels) + ')/$'
        urlpatterns.append(re_path(regex, self.api_admin_view(self.app_index), name='app_list'))

        # add model_admin views
        for model, model_admin in self._registry.items():
            urlpatterns += [
                path('%s/%s/' % (model._meta.app_label, model._meta.model_name), include(model_admin.urls)),
            ]

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
            root_urls = [url for url in urlpatterns if
                         isinstance(url, URLPattern) and url.name and url.name not in excluded_url_names]
            root_view = api_views.AdminAPIRootView.as_view(root_urls=root_urls)
            urlpatterns.append(path('', root_view, name='api-root'))

        if self.include_final_catch_all_view:
            urlpatterns.append(re_path(r'(?P<url>.*)$', self.catch_all_view, name='final_catch_all'))

        return urlpatterns

    @property
    def urls(self):
        return self.get_urls(), self.name, self.name

    # todo understand this method more
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
                    model_dict['admin_url'] = reverse('api_admin:%s_%s_changelist' % info, current_app=self.name)
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

    # admin site wide views
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

    def site_context_view(self, request):
        defaults = {
            'permission_classes': self.default_permission_classes,
        }
        return api_views.SiteContextView.as_view(**defaults)(request, admin_site=self)

    def admin_log_view(self, request):
        defaults = {
            'permission_classes': self.default_permission_classes,
            'serializer_class': self.log_entry_serializer,
            'pagination_class': self.default_pagination_class,
        }
        return api_views.AdminLogView.as_view(**defaults)(request)


site = APIAdminSite(name='api_admin')
