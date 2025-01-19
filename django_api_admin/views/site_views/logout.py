from django.contrib.auth import logout
from django.utils.translation import gettext_lazy as _

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView


class LogoutView(APIView):
    """
    Logout and display a 'you are logged out ' message.
    """
    permission_classes = []

    def post(self, request):
        logout(request)
        return Response({"detail": _("You are logged out.")}, status=status.HTTP_200_OK)

    def get(self, request):
        return self.post(request)
