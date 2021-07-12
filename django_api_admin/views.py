from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from django_api_admin.serializers import LoginSerializer, UserSerializer
from django.contrib.auth import login


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
