from django.utils.translation import gettext_lazy as _

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.reverse import reverse
from rest_framework.response import Response

from rest_framework.views import APIView


class ListView(APIView):
    """
    Return a list containing all instances of this model.
    """

    serializer_class = None
    permission_classes = []
    model_admin = None

    def get(self, request):
        queryset = self.model_admin.get_queryset()
        page = self.model_admin.admin_site.paginate_queryset(
            queryset, request, view=self)
        serializer = self.serializer_class(page, many=True)
        data = serializer.data
        info = (
            self.model_admin.admin_site.name,
            self.model_admin.model._meta.app_label,
            self.model_admin.model._meta.model_name
        )
        pattern = '%s:%s_%s_detail'

        for item in data:
            item['detail_url'] = reverse(pattern % info, kwargs={
                'object_id': item['pk']}, request=request)
        return Response(data, status=status.HTTP_200_OK)
