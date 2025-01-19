from django.utils.translation import gettext_lazy as _

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView


class SiteContextView(APIView):
    """
    Returns the Attributes of AdminSite class (e.g. site_title, site_header)
    """
    permission_classes = []

    def get(self, request, admin_site):
        context = admin_site.each_context(request)
        return Response(context, status=status.HTTP_200_OK)
