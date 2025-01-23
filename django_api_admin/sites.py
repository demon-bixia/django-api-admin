"""
API admin site.
"""
from django.apps import apps
from django.contrib.admin import AdminSite
from django.contrib.admin.sites import AlreadyRegistered
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ImproperlyConfigured
from django.db.models.base import ModelBase
from django.urls import NoReverseMatch, reverse, URLPattern, include, path, re_path
from django.utils.text import capfirst
from django.contrib.contenttypes import views as contenttype_views

from django_api_admin import actions
from django_api_admin import serializers as api_serializers
from django_api_admin.admins.model_admin import APIModelAdmin
from django_api_admin.pagination import AdminLogPagination, AdminResultsListPagination
from django_api_admin.permissions import IsAdminUser

from django_api_admin.views.site_views.admin_api_root import AdminAPIRootView
from django_api_admin.views.site_views.admin_log import AdminLogView
from django_api_admin.views.site_views.app_index import AppIndexView
from django_api_admin.views.site_views.autocomplete import AutoCompleteView
from django_api_admin.views.site_views.index import IndexView
from django_api_admin.views.site_views.language_catalog import LanguageCatalogView
from django_api_admin.views.site_views.obtain_token import ObtainTokenView
from django_api_admin.views.site_views.password_change import PasswordChangeView
from django_api_admin.views.site_views.site_context import SiteContextView
from django_api_admin.views.site_views.user_information import UserInformation

from rest_framework_simplejwt.views import TokenRefreshView


UserModel = get_user_model()


class APIAdminSite(AdminSite):
    """
    Encapsulates an instance of the django admin application.
    """
    # default model admin class
    admin_class = APIModelAdmin

    # optional views
    include_view_on_site_view = True
    include_root_view = True

    # default permissions
    default_permission_classes = [IsAdminUser, ]

    # default serializers
    token_serializer = api_serializers.ObtainTokenSerializer
    password_change_serializer = api_serializers.PasswordChangeSerializer
    log_entry_serializer = api_serializers.LogEntrySerializer
    user_serializer = api_serializers.UserSerializer

    # default result pagination style
    default_pagination_class = AdminResultsListPagination
    default_log_pagination_class = AdminLogPagination

    def __init__(self, include_auth=False, *args, **kwargs):

        super().__init__(*args, **kwargs)

        # replace default delete selected with a custom delete_selected action
        self._actions = {'delete_selected': actions.delete_selected}
        self._global_actions = self._actions.copy()
        self.admin_class = self.admin_class or APIModelAdmin

        # if include_auth is set to True then include default UserModel and Groups
        if include_auth:
            self.register([UserModel, Group])

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
                raise AlreadyRegistered(
                    'The model %s is already registered ' % model.__name__)

            if not model._meta.swapped:
                if options:
                    options['__module__'] = __name__
                    admin_class = type("%sAdmin" %
                                       model.__name__, (admin_class,), options)

                # Instantiate the admin class to save in the registry
                self._registry[model] = admin_class(model, self)

    def get_urls(self):
        urlpatterns = [
            path('index/', self.get_index_view(), name='index'),
            path('user_info/', self.get_user_info_view(), name='user_info'),
            path('token/', self.get_token_view(), name='token_obtain_pair'),
            path('token/refresh/', TokenRefreshView.as_view(),
                 name='token_refresh'),
            path('password_change/', self.get_password_change_view(),
                 name='password_change'),
            path('autocomplete/', self.autocomplete_view(),
                 name='autocomplete'),
            path('jsoni18n/', self.get_i18n_javascript_view(),
                 name='language_catalog'),
            path('site_context/', self.get_site_context_view(),
                 name='site_context'),
            path('admin_log/', self.get_admin_log_view(),
                 name='admin_log'),
        ]

        # add the app detail view
        valid_app_labels = [model._meta.app_label for model,
                            model_admin in self._registry.items()]
        regex = r'^(?P<app_label>' + '|'.join(valid_app_labels) + ')/$'
        urlpatterns.append(
            re_path(regex, self.get_app_index_view(), name='app_list'))

        # add model_admin urls
        for model, model_admin in self._registry.items():
            urlpatterns += [
                path('%s/%s/' % (model._meta.app_label,
                                 model._meta.model_name), include(model_admin.urls)),
            ]

        # add optional views
        if self.include_view_on_site_view:
            urlpatterns.append(path(
                'r/<int:content_type_id>/<path:object_id>/',
                contenttype_views.shortcut,
                name='view_on_site',
            ))

        # add api_root for browsable api.
        if self.include_root_view:
            # remove detail, redirect urls and urls with no names
            excluded_url_names = ['app_list',
                                  'view_on_site', 'language_catalog']
            root_urls = [url for url in urlpatterns if
                         isinstance(url, URLPattern) and url.name and url.name not in excluded_url_names]
            root_view = AdminAPIRootView.as_view(
                root_urls=root_urls)
            urlpatterns.append(path('', root_view, name='api-root'))
        return urlpatterns

    @property
    def urls(self):
        return self.get_urls(), self.name, self.name

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

            info = (self.name, app_label, model._meta.model_name)
            model_dict = {
                'name': capfirst(model._meta.verbose_name_plural),
                'object_name': model._meta.object_name,
                'perms': perms,
                'list_url': None,
                'changelist_url': None,
                'add_url': None,
                'perform_action_url': None,
            }

            if perms.get('change') or perms.get('view'):
                model_dict['view_only'] = not perms.get('change')
                try:
                    model_dict['list_url'] = request.build_absolute_uri(
                        reverse('%s:%s_%s_list' % info, current_app=self.name))
                    model_dict['changelist_url'] = request.build_absolute_uri(
                        reverse('%s:%s_%s_changelist' % info, current_app=self.name))
                    model_dict['perform_action_url'] = request.build_absolute_uri(
                        reverse('%s:%s_%s_perform_action' % info, current_app=self.name))
                except NoReverseMatch:
                    pass

            if perms.get('add'):
                try:
                    model_dict['add_url'] = request.build_absolute_uri(
                        reverse('%s:%s_%s_add' % info, current_app=self.name))
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

    def get_app_list(self, request, app_label=None):
        """
        Return a sorted list of all the installed apps that have been
        registered in this site.
        """
        app_dict = self._build_app_dict(request, app_label)

        # Sort the apps alphabetically.
        app_list = sorted(app_dict.values(), key=lambda x: x["name"].lower())

        # Sort the models alphabetically within each app.
        for app in app_list:
            app["models"].sort(key=lambda x: x["name"])

        return app_list

    def each_context(self, request):
        """
        Return a dictionary of variables to put in the template context for
        *every* page in the admin site.

        For sites running on a subpath, use the SCRIPT_NAME value if site_url
        hasn't been customized.
        """
        script_name = request.META["SCRIPT_NAME"]
        site_url = (
            script_name if self.site_url == "/" and script_name else self.site_url
        )
        return {
            "site_title": self.site_title,
            "site_header": self.site_header,
            "site_url": site_url,
            "has_permission": request.user.is_active and request.user.is_staff,
            "available_apps": self.get_app_list(request),
            "is_popup": False,
            "is_nav_sidebar_enabled": self.enable_nav_sidebar,
        }

    def paginate_queryset(self, queryset, request, view=None):
        paginator = self.default_pagination_class()
        return paginator.paginate_queryset(queryset.order_by('pk'), request, view=view)

    def get_log_entry_serializer(self):
        return type('LogEntrySerializer', (self.log_entry_serializer,), {
            'user': self.user_serializer(read_only=True),
        })

    def get_index_view(self):
        defaults = {
            'permission_classes': self.default_permission_classes,
            'admin_site': self
        }
        return IndexView.as_view(**defaults)

    def get_app_index_view(self):
        defaults = {
            'permission_classes': self.default_permission_classes,
            'admin_site': self
        }
        return AppIndexView.as_view(**defaults)

    def get_token_view(self):
        defaults = {
            'permission_classes': [],
            'serializer_class': self.token_serializer,
            'admin_site': self,
        }
        return ObtainTokenView.as_view(**defaults)

    def get_password_change_view(self):
        defaults = {
            'permission_classes': self.default_permission_classes,
            'serializer_class': self.password_change_serializer,
        }
        return PasswordChangeView.as_view(**defaults)

    def get_i18n_javascript_view(self):
        defaults = {
            'permission_classes': self.default_permission_classes,
        }
        return LanguageCatalogView.as_view(**defaults)

    def autocomplete_view(self):
        defaults = {
            'permission_classes': self.default_permission_classes,
            'admin_site': self
        }
        return AutoCompleteView.as_view(**defaults)

    def get_site_context_view(self):
        defaults = {
            'permission_classes': self.default_permission_classes,
            'admin_site': self
        }
        return SiteContextView.as_view(**defaults)

    def get_admin_log_view(self):
        defaults = {
            'permission_classes': self.default_permission_classes,
            'pagination_class': self.default_log_pagination_class,
            'serializer_class': self.get_log_entry_serializer(),
            'admin_site': self
        }
        return AdminLogView.as_view(**defaults)

    def get_user_info_view(self):
        defaults = {
            'permission_classes': self.default_permission_classes,
            'serializer_class': self.user_serializer
        }
        return UserInformation.as_view(**defaults)


site = APIAdminSite(name='api_admin', include_auth=True)
