from django.contrib.admin.views.autocomplete import AutocompleteJsonView
from django.contrib.auth import login, logout
from django.utils.translation import gettext_lazy as _
from django.views.i18n import JSONCatalog
from rest_framework import status
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView


class LoginView(APIView):
    """
    Allow users to login using username and password
    """
    serializer_class = None
    user_serializer_class = None
    permission_classes = []

    def post(self, request):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        if serializer.is_valid():
            login(request, serializer.get_user())
            user_serializer = self.user_serializer_class(request.user)
            return Response({'user': user_serializer.data}, status=status.HTTP_200_OK)

        for error in serializer.errors.get('non_field_errors', []):
            if error.code == 'permission_denied':
                return Response(serializer.errors, status=status.HTTP_403_FORBIDDEN)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    """
    logout and display a 'your are logged out ' message.
    """
    user_serializer_class = None
    permission_classes = []

    def post(self, request):
        user_serializer = self.user_serializer_class(request.user)
        message = _("You are logged out.")
        logout(request)
        return Response({'user': user_serializer.data, 'message': message},
                        status=status.HTTP_200_OK)

    def get(self, *args, **kwargs):
        return self.post(*args, **kwargs)


class PasswordChangeView(APIView):
    """
        Handle the "change password" task -- both form display and validation.
    """
    serializer_class = None
    permission_classes = []

    def post(self, request):
        serializer_class = self.serializer_class
        serializer = serializer_class(data=request.data, context={'user': request.user})
        if serializer.is_valid():
            serializer.save()
            return Response({'message': _('Your password was changed')},
                            status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class IndexView(APIView):
    """
    Return json object that lists all of the installed
    apps that have been registered by the admin site.
    """
    permission_classes = []

    def get(self, request, admin_site):
        # todo replace hard coded admin site

        app_list = admin_site.get_app_list(request)

        # add a url to app_index in every app in app_list
        for app in app_list:
            url = reverse(f'{admin_site.name}:app_list', kwargs={'app_label': app['app_label']}, request=request)
            app['url'] = url

        data = {
            'app_list': app_list,
            'context': {
                **admin_site.each_context(request),
            },
        }

        request.current_app = admin_site.name

        return Response(data, status=status.HTTP_200_OK)


class AppIndexView(APIView):
    """
    Lists models inside a given app.
    """

    permission_classes = []

    def get(self, request, app_label, admin_site):
        app_dict = admin_site._build_app_dict(request, app_label)

        if not app_dict:
            return Response({'message': 'The requested admin page does not exist.'}, status=status.HTTP_404_NOT_FOUND)

        # Sort the models alphabetically within each app.
        app_dict['models'].sort(key=lambda x: x['name'])
        data = {
            'app_label': app_label,
            'app': app_dict,
            'context': {
                **admin_site.each_context(request),
            },
        }

        return Response(data, status=status.HTTP_200_OK)


class LanguageCatalogView(APIView):
    """
      Returns json object with django.contrib.admin i18n translation catalog
      to be used by a client site javascript library
    """
    permission_classes = []

    def get(self, request):
        response = JSONCatalog.as_view(packages=['django.contrib.admin'])(request)
        return Response({'context': response.content}, status=response.status_code)


class AutoCompleteView(APIView):
    """Handle AutocompleteWidget's AJAX requests for data."""
    permission_classes = []

    def get(self, request, admin_site=None):
        response = AutocompleteJsonView.as_view(admin_site=admin_site)(request)
        return Response({'content': response.content}, status=response.status_code)


class AdminAPIRootView(APIView):
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
            elif not request.user.is_authenticated and url.name in ('logout', 'password_change'):
                continue
            data[url.name] = reverse(namespace + ':' + url.name, request=request, args=args, kwargs=kwargs)

        return Response(data or {}, status=status.HTTP_200_OK)
