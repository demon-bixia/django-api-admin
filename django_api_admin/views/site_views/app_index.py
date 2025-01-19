from django.utils.translation import gettext_lazy as _

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView


class AppIndexView(APIView):
    """
    Lists models inside a given app.
    """

    permission_classes = []

    def get(self, request, app_label, admin_site):
        app_dict = admin_site._build_app_dict(request, app_label)

        if not app_dict:
            return Response({'detail': _('The requested admin page does not exist.')},
                            status=status.HTTP_404_NOT_FOUND)

        # Sort the models alphabetically within each app.
        app_dict['models'].sort(key=lambda x: x['name'])

        data = {
            'app_label': app_label,
            'app': app_dict,
        }

        return Response(data, status=status.HTTP_200_OK)
