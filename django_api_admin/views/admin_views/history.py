from django.contrib.admin.models import LogEntry
from django.utils.translation import gettext_lazy as _
from django.contrib.admin.utils import unquote
from django.contrib.admin.options import (get_content_type_for_model)

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied


class HistoryView(APIView):
    """
    History of actions that happened to this object.
    """
    permission_classes = []
    serializer_class = None

    def get(self, request, object_id, model_admin):
        model = model_admin.model
        opts = model._meta
        obj = model_admin.get_object(request, unquote(object_id))

        # if the object does not exist respond with 404 response
        if obj is None:
            msg = _("%(name)s with ID “%(key)s” doesn't exist. Perhaps it was deleted?") % {
                'name': opts.verbose_name,
                'key': unquote(object_id),
            }
            return Response({'detail': msg}, status=status.HTTP_404_NOT_FOUND)

        # if user has no change permission on this model then respond permission Denied
        if not model_admin.has_view_or_change_permission(request, obj):
            raise PermissionDenied

        # Then get the history for this object.
        action_list = LogEntry.objects.filter(
            object_id=unquote(object_id),
            content_type=get_content_type_for_model(model)
        ).select_related().order_by('action_time')

        # paginate the action_list
        page = model_admin.admin_site.paginate_queryset(
            action_list, request, view=self)

        # serialize the LogEntry queryset
        serializer = self.serializer_class(page, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)
