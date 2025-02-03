from django.utils.translation import gettext_lazy as _

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.reverse import reverse


class AdminAPIRootView(APIView):
    """
    A list of all root urls in django_api_admin
    """
    root_urls = None

    def get(self, request, *args, **kwargs):
        namespace = request.resolver_match.namespace
        data = dict()

        for url in self.root_urls:
            data[url.name] = reverse(
                namespace + ':' + url.name, args=args, kwargs=kwargs, request=request)

        return Response(data or {}, status=status.HTTP_200_OK)
