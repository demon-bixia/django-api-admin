from django.contrib.contenttypes.views import shortcut as view_on_site
from django.urls import re_path, path
from rest_framework import views, status
from rest_framework.response import Response
from rest_framework.routers import Route, SimpleRouter
from rest_framework.reverse import reverse


class AdminAPIRootView(views.APIView):
    """
    A list of all root urls in django_api_admin
    """
    root_urls = None

    def get(self, request, *args, **kwargs):
        namespace = request.resolver_match.namespace
        data = dict()

        for url in self.root_urls:
            if request.user.is_authenticated and url.name == 'login':
                continue
            elif not request.user.is_authenticated and url.name == 'logout':
                continue
            data[url.name] = reverse(namespace + ':' + url.name, request=request, args=args, kwargs=kwargs)

        return Response(data or {}, status=status.HTTP_200_OK)


class AdminRouter(SimpleRouter):
    """
    Automatically constructs urls for AdminViewSet.
    """
    # admin site
    admin_site = None

    # optional views
    final_catch_all_view = False
    include_root_view = True
    view_on_site_view = False

    # route patterns
    routes = [
        Route(
            url=r'^login{trailing_slash}$',
            mapping={'post': 'login'},
            name='login',
            detail=False,
            initkwargs={'suffix': 'Login'}
        ),
        Route(
            url=r'^logout{trailing_slash}$',
            mapping={
                'post': 'logout',
                'get': 'logout',
            },
            name='logout',
            detail=False,
            initkwargs={'suffix': 'Logout'}
        ),
        Route(
            url=r'^password_change{trailing_slash}$',
            mapping={'post': 'password_change'},
            name='password_change',
            detail=False,
            initkwargs={'suffix': 'Password Change'}
        ),

        Route(
            url=r'^jsi18n{trailing_slash}$',
            mapping={'get': 'language_catalog'},
            name='language_catalog',
            detail=False,
            initkwargs={'suffix': 'Translation Catalog'}
        )
    ]

    def __init__(self, admin_site, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.admin_site = self.admin_site or admin_site

        # if there is no root view the index view url should be '/'
        admin_index_route = Route(
            url=r'^$',
            mapping={
                'get': 'index'
            },
            name='index',
            detail=False,
            initkwargs={'suffix': 'Home'}
        )
        if self.include_root_view:
            admin_index_route = Route(
                url=r'^index{trailing_slash}$',
                mapping={
                    'get': 'index'
                },
                name='index',
                detail=False,
                initkwargs={'suffix': 'Home'}
            )
        self.routes.insert(0, admin_index_route)

    def get_default_basename(self, viewset=None):
        return 'admin'

    def get_urls(self):
        """
        Generate the list of URL patterns, including a final_catch_all_view,
        and a view_on_site view.
        """
        urls = super().get_urls()

        if self.include_root_view:
            # view_on_site view and the rest of the urls that are detail
            excluded_url_names = ['view_on_site', 'final_catch_all',
                                  *[route.name for route in self.routes if route.detail]]
            root_urls = [url for url in urls if url.name not in excluded_url_names]
            root_view = AdminAPIRootView.as_view(root_urls=root_urls)
            root_url = re_path(r'^$', root_view, name='api-root')
            urls.append(root_url)

        # add the app detail view
        valid_app_labels = [model._meta.app_label for model, model_admin in self.admin_site._registry.items()]
        for prefix, viewset, basename in self.registry:
            if prefix == self.admin_site.name:
                regex = r'^(?P<app_label>' + '|'.join(valid_app_labels) + ')/$'
                mapping = self.get_method_map(viewset, {'get': 'app_index'})
                initkwargs = {'suffix': 'Models', 'detail': True, 'basename': basename}
                view = viewset.as_view(mapping, **initkwargs)
                urls.append(re_path(regex, view, name='app_list'))

        if self.view_on_site_view:
            view_on_site_url = path('r/<int:content_type_id>/<path:object_id>/', view_on_site, name='view_on_site')
            urls.append(view_on_site_url)

        # finally add the final catch all view
        if self.final_catch_all_view:
            catch_all_view = self.admin_site.catch_all_view
            catch_all_view_url = re_path(r'(?P<url>.*)$', catch_all_view, name='final_catch_all')
            urls.append(catch_all_view_url)

        return urls

    @property
    def urls(self):
        return self.get_urls()
