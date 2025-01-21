from django.utils.translation import gettext_lazy as _

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.reverse import reverse


class IndexView(APIView):
    """
    Return json object that lists all the installed
    apps that have been registered by the admin site.
    """
    permission_classes = []
    admin_site = None

    def get(self, request):
        app_list = self.admin_site.get_app_list(request)

        # add an url to app_index in every app in app_list
        for app in app_list:
            app['url'] = reverse(f'{self.admin_site.name}:app_list', kwargs={
                                 'app_label': app['app_label']}, request=request)
        data = {'app_list': app_list}
        request.current_app = self.admin_site.name
        return Response(data, status=status.HTTP_200_OK)
