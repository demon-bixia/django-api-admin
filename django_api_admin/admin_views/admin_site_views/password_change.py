from django.utils.translation import gettext_lazy as _

from rest_framework import status
from rest_framework.response import Response

from rest_framework.views import APIView


class PasswordChangeView(APIView):
    """
    Handle the "change password" task -- both form display and validation.
    """
    serializer_class = None
    permission_classes = []
    admin_site = None

    def post(self, request):
        serializer_class = self.serializer_class
        serializer = serializer_class(
            data=request.data, context={'user': request.user})
        if serializer.is_valid():
            serializer.save()
            return Response({'detail': _('Your password was changed')},
                            status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
