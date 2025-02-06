from django.utils.translation import gettext_lazy as _

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import NotFound

from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample

from django_api_admin.utils.get_form_fields import get_form_fields
from django_api_admin.openapi import CommonAPIResponses, APIResponseExamples
from django_api_admin.serializers import FormFieldsSerializer


class IncorrectLookupParameters(Exception):
    pass


class HandleActionView(APIView):
    """
    Preform admin actions on objects using json.
    """
    permission_classes = []
    model_admin = None

    @extend_schema(
        responses={
            200: OpenApiResponse(
                description="Successfully returned the field attributes list",
                response=FormFieldsSerializer,
                examples=[
                    APIResponseExamples.field_attributes()
                ]
            ),
            403: CommonAPIResponses.permission_denied(),
            401: CommonAPIResponses.unauthorized()
        },
    )
    def get(self, request):
        """
        Handle GET requests to retrieve a list of form field attributes for
        the admin action.
        """
        serializer = self.model_admin.get_action_serializer(request)()
        form_fields = get_form_fields(serializer)
        return Response({'fields': form_fields}, status=status.HTTP_200_OK)

    @extend_schema(
        responses={
            200: OpenApiResponse(
                description=_(
                    "Action executed successfully on selected objects"),
                response=dict,
                examples=[
                    OpenApiExample(
                        name=_("Success Response"),
                        summary=_("Example of a successful action execution"),
                        description=_(
                            "Returns a success message after performing the selected action on chosen objects"),
                        value={"detail": "action was performed successfully"},
                        status_codes=["200"]
                    )
                ]
            ),
            403: CommonAPIResponses.permission_denied(),
            401: CommonAPIResponses.unauthorized()
        }
    )
    def post(self, request):
        serializer = self.model_admin.get_action_serializer(
            request)(data=request.data)
        # validate the action selected
        if serializer.is_valid():
            # preform the action on the selected items
            action = serializer.validated_data.get('action')
            select_across = serializer.validated_data.get('select_across')
            func = self.model_admin.get_actions(request)[action][0]
            try:
                cl = self.model_admin.get_changelist_instance(request)
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
            response = func(self.model_admin, request, queryset)

            if response:
                return response
            else:
                msg = _("action was performed successfully")
                return Response({'detail': msg}, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_serializer_class(self):
        return self.model_admin.get_action_serializer(request=self.request)
