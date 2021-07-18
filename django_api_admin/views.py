from django.contrib.auth import login, logout
from django.utils.translation import gettext_lazy as _
from django.views.i18n import JSONCatalog
from rest_framework import status, viewsets
from rest_framework.response import Response

from django_api_admin.permissions import IsAdminUser
from django_api_admin.serializers import LoginSerializer, UserSerializer, PasswordChangeSerializer


# todo add custom caching and csrf checking
class AdminSiteViewSet(viewsets.ViewSet):
    # default serializers
    login_serializer_class = LoginSerializer
    user_serializer_class = UserSerializer
    password_change_serializer_class = PasswordChangeSerializer

    # default permissions
    permission_classes = [IsAdminUser, ]

    def login(self, request, extra_context=None):
        """
        Allow users to login using username and password
        """

        serializer = self.login_serializer_class(data=request.data, context={'request': request})
        if serializer.is_valid():
            login(request, serializer.get_user())
            user_serializer = self.user_serializer_class(request.user)
            return Response({'user': user_serializer.data, **(extra_context or {})}, status=status.HTTP_200_OK)

        for error in serializer.errors['non_field_errors']:
            if error.code == 'permission_denied':
                return Response(serializer.errors, status=status.HTTP_403_FORBIDDEN)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def logout(self, request, extra_context=None):
        """
        logout and display a 'your are logged out ' message.
        """
        user_serializer = self.user_serializer_class(request.user)
        message = _("You are logged out.")
        logout(request)
        return Response({'user': user_serializer.data, 'message': message, **(extra_context or {})},
                        status=status.HTTP_200_OK)

    def password_change(self, request, extra_context=None):
        """
            Handle the "change password" task -- both form display and validation.
        """

        serializer = self.password_change_serializer_class(data=request.data, context={'user': request.user})
        if serializer.is_valid():
            serializer.save()
            return Response({'message': _('Your password was changed'), **(extra_context or {})},
                            status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def index(self, request, extra_context=None):
        """
        Return json object that lists all of the installed
        apps that have been registered by the admin site.
        """
        from django_api_admin.sites import site as admin_site

        app_list = admin_site.get_app_list(request)

        data = {
            **admin_site.each_context(request),
            'app_list': app_list,
            **(extra_context or {}),
        }

        request.current_app = admin_site.name

        return Response(data, status=status.HTTP_200_OK)

    def app_index(self, request, app_label, extra_context=None):
        """
        Lists models inside a given app.
        """
        from django_api_admin.sites import site as admin_site

        app_dict = admin_site._build_app_dict(request, app_label)

        if not app_dict:
            return Response({'message': 'The requested admin page does not exist.'}, status=status.HTTP_404_NOT_FOUND)

        # Sort the models alphabetically within each app.
        app_dict['models'].sort(key=lambda x: x['name'])
        data = {
            **admin_site.each_context(request),
            'app_list': [app_dict],
            'app_label': app_label,
            **(extra_context or {}),
        }

        return Response(data, status=status.HTTP_200_OK)

    def language_catalog(self, request, extra_context=None):
        """
        Returns json object with django.contrib.admin i18n translation catalog
        to be used by a client site javascript library
        """
        response = JSONCatalog.as_view(packages=['django.contrib.admin'])(request)
        return Response({'context': response.content}, status=status.HTTP_200_OK)
1