from django.middleware.csrf import get_token
from django.utils.translation import gettext_lazy as _

from rest_framework.response import Response
from rest_framework.views import APIView


class CsrfTokenView(APIView):
    serializer_class = None
    permission_classes = []

    def get(self, request):
        return Response({'csrftoken': get_token(request)})
