from django.contrib.auth import login
from django.utils.translation import gettext_lazy as _

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from django_api_admin.utils.get_form_fields import get_form_fields


class LoginView(APIView):
    """
    Allow users to login using username and password.
    """
    serializer_class = None
    permission_classes = []

    def get(self, request, admin_site):
        serializer = self.serializer_class()
        form_fields = get_form_fields(serializer)
        return Response({'fields': form_fields}, status=status.HTTP_200_OK)

    def post(self, request, admin_site):
        serializer = self.serializer_class(
            data=request.data, context={'request': request})
        if serializer.is_valid():
            user = serializer.get_user()
            login(request, user)
            user_serializer = admin_site.user_serializer(user)
            data = {
                'detail': _('you are logged in successfully'),
                'user': user_serializer.data
            }
            return Response(data, status=status.HTTP_200_OK)

        for error in serializer.errors.get('non_field_errors', []):
            if error.code == 'permission_denied':
                return Response(serializer.errors, status=status.HTTP_403_FORBIDDEN)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
