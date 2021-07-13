from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django_api_admin.serializers import LoginSerializer, UserSerializer, PasswordChangeSerializer
from django.contrib.auth import login, logout
from django.utils.translation import gettext_lazy as _


class LoginView(APIView):
    """
    Allow users to login using username and password
    """

    def post(self, request, extra_context=None):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            login(request, serializer.get_user())
            user_serializer = UserSerializer(request.user)
            return Response({'user': user_serializer.data, **(extra_context or {})}, status=status.HTTP_200_OK)

        for error in serializer.errors['non_field_errors']:
            if error.code == 'permission_denied':
                return Response(serializer.errors, status=status.HTTP_403_FORBIDDEN)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    """
    logout and display a 'your are logged out ' message.
    """

    def get(self, request, extra_context=None):
        user_serializer = UserSerializer(request.user)
        message = _("You are logged out.")
        logout(request)
        return Response({'user': user_serializer.data, 'message': message, **(extra_context or {})},
                        status=status.HTTP_200_OK)

    def post(self, request, extra_context=None):
        return self.get(request, extra_context)


class PasswordChangeView(APIView):
    """
        Handle the "change password" task -- both form display and validation.
    """

    def post(self, request, extra_context=None):
        serializer = PasswordChangeSerializer(data=request.data, context={'user': request.user})
        if serializer.is_valid():
            serializer.save()
            return Response({'message': _('Your password was changed'), **(extra_context or {})},
                            status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class IndexView(APIView):
    """
    Return json object that lists all of the installed
    apps that have been registered by the admin site.
    """

    def get(self, request, admin_site, extra_context=None):
        app_list = admin_site.get_app_list(request)

        data = {
            **admin_site.each_context(request),
            'app_list': app_list,
            **(extra_context or {}),
        }

        request.current_app = admin_site.name

        return Response(data, status=status.HTTP_200_OK)


# todo change url keyword argument to json
class AppIndexView(APIView):
    def get(self, request, admin_site, app_label, extra_context=None):
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
