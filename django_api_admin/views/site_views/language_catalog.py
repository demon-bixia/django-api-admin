from django.utils.translation import gettext_lazy as _
from django.views.i18n import JSONCatalog

from rest_framework.response import Response
from rest_framework.views import APIView


class LanguageCatalogView(APIView):
    """
      Returns json object with django.contrib.admin i18n translation catalog
      to be used by a client site javascript library
    """
    permission_classes = []

    def get(self, request):
        response = JSONCatalog.as_view(packages=['django_api_admin'])(request)
        return Response(response.content, status=response.status_code)
