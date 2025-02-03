from django.utils.translation import gettext_lazy as _

from rest_framework.response import Response

from rest_framework.views import APIView


class UserInformation(APIView):
    serializer_class = None
    permission_classes = []
    admin_site = None

    def get(self, request):
        serializer = self.serializer_class(request.user)
        return Response({'user': serializer.data})
