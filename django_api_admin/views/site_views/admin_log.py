import json

from django.utils.translation import gettext_lazy as _

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView


class AdminLogView(APIView):
    """
    Returns a list of actions that were preformed using django admin.
    """
    serializer_class = None
    pagination_class = None
    permission_classes = []
    ordering_fields = ['action_time', '-action_time']

    def get(self, request, admin_site):
        from django.contrib.admin.models import LogEntry

        queryset = LogEntry.objects.all()

        # order the queryset
        try:
            ordering = self.request.query_params.get('o')
            if ordering is not None:
                if ordering not in self.ordering_fields:
                    raise KeyError
                queryset = queryset.order_by(ordering)
        except:
            return Response({'detail': 'Wrong ordering field set.'}, status=status.HTTP_400_BAD_REQUEST)

        # filter the queryset.
        try:
            object_id = self.request.query_params.get('object_id')
            if object_id is not None:
                queryset = queryset.filter(object_id=object_id)
        except:
            return Response({'detail': 'Bad filters.'}, status=status.HTTP_400_BAD_REQUEST)

        # paginate queryset.
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)

        # serialize queryset.
        serializer = self.serializer_class(page, many=True)

        return Response({
            'action_list': self.serialize_messages(serializer.data),
            'config': self.get_config(page, queryset)},
            status=status.HTTP_200_OK)

    def serialize_messages(self, data):
        for idx, item in enumerate(data, start=0):
            data[idx]['change_message'] = json.loads(
                item['change_message'] or '[]')
        return data

    def get_config(self, page, queryset):
        return {
            'result_count': len(page),
            'full_result_count': queryset.count(),
        }
