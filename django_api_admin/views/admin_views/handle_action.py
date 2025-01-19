from django.utils.translation import gettext_lazy as _
from django.contrib.admin.options import (IncorrectLookupParameters)

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import NotFound

from django_api_admin.utils.get_form_fields import get_form_fields


class HandleActionView(APIView):
    """
        Preform admin actions using json.
        json object would look like:
        {
        action: 'delete_selected',
        selected_ids: [
                1,
                2,
                3
            ],
        select_across: false
        }
    """
    permission_classes = []
    serializer_class = None

    def get(self, request, admin):
        serializer = self.serializer_class()
        form_fields = get_form_fields(serializer)
        return Response({'fields': form_fields}, status=status.HTTP_200_OK)

    def post(self, request, model_admin):
        serializer = self.serializer_class(data=request.data)
        # validate the action selected
        if serializer.is_valid():
            # preform the action on the selected items
            action = serializer.validated_data.get('action')
            select_across = serializer.validated_data.get('select_across')
            func = model_admin.get_actions(request)[action][0]
            try:
                cl = model_admin.get_changelist_instance(request)
            except IncorrectLookupParameters as e:
                raise NotFound(str(e))
            queryset = cl.get_queryset(request)

            # get a list of pks of selected changelist items
            selected = request.data.get('selected_ids', None)
            if not selected and not select_across:
                msg = _("Items must be selected in order to perform "
                        "actions on them. No items have been changed.")
                return Response({'detail': msg}, status=status.HTTP_400_BAD_REQUEST)
            if not select_across:
                queryset = queryset.filter(pk__in=selected)

            # if the action returns a response
            response = func(model_admin, request, queryset)

            if response:
                return response
            else:
                msg = _("action was performed successfully")
                return Response({'detail': msg}, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
