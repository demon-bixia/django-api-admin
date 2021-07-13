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

    def post(self, request):
        serializer = LoginSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            login(request, serializer.get_user())
            user_serializer = UserSerializer(request.user)
            return Response(user_serializer.data, status=status.HTTP_200_OK)

        for error in serializer.errors['non_field_errors']:
            if error.code == 'permission_denied':
                return Response(serializer.errors, status=status.HTTP_403_FORBIDDEN)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    """
    logout and display a 'your are logged out ' message.
    """

    def get(self, request):
        user_serializer = UserSerializer(request.user)
        message = _("You are logged out.")
        logout(request)
        return Response({'user': user_serializer.data, 'message': message}, status=status.HTTP_200_OK)

    def post(self, request):
        return self.get(request)


class PasswordChangeView(APIView):
    """
        Handle the "change password" task -- both form display and validation.
    """

    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={'user': request.user})
        if serializer.is_valid():
            serializer.save()
            return Response({'message': _('Your password was changed')}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
