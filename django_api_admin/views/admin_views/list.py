from django.utils.translation import gettext_lazy as _

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.reverse import reverse
from rest_framework.response import Response


class ListView(APIView):
    """
    Return a list containing all instances of this model.
    """

    serializer_class = None
    permission_classes = []

    def get(self, request, admin):
        queryset = admin.get_queryset(request)
        page = admin.admin_site.paginate_queryset(queryset, request, view=self)
        serializer = self.serializer_class(page, many=True)
        data = serializer.data
        info = (
            admin.admin_site.name,
            admin.model._meta.app_label,
            admin.model._meta.model_name
        )
        pattern = '%s:%s_%s_detail'

        for item in data:
            item['detail_url'] = reverse(pattern % info, kwargs={
                'object_id': item['pk']}, request=request)
        return Response(data, status=status.HTTP_200_OK)
