from django.utils.translation import gettext_lazy as _

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample

from django_api_admin.utils.get_form_fields import get_form_fields
from django_api_admin.openapi import CommonAPIResponses, APIResponseExamples
from django_api_admin.serializers import FormFieldsSerializer


class PasswordChangeView(APIView):
    """
    Handles the password change request for a user.
    """
    serializer_class = None
    permission_classes = []
    admin_site = None

    @extend_schema(
        responses={
            200: OpenApiResponse(
                description=_(
                    "Successfully returned the field attributes list"),
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
        Handles GET requests to retrieve form fields for password change.
        """
        data = dict()
        serializer = self.serializer_class()
        data['fields'] = get_form_fields(serializer)
        return Response(data, status=status.HTTP_200_OK)

    @extend_schema(
        responses={
            200: OpenApiResponse(
                description=_("Successful change of the user's password"),
                response=dict,
                examples=[
                    OpenApiExample(
                        name=_("Success Response"),
                        summary=_(
                            "Example of a successful password change response"),
                        description=_(
                            "Returns a message confirming the password change"),
                        value={"detail": "Your password was changed"},
                        status_codes=["200"]
                    )
                ],
            ),
            403: CommonAPIResponses.permission_denied(),
            401: CommonAPIResponses.unauthorized()
        }
    )
    def post(self, request):
        """
        This view processes POST requests to change a user's password. 
        """
        serializer_class = self.serializer_class
        serializer = serializer_class(
            data=request.data, context={'user': request.user})
        if serializer.is_valid():
            serializer.save()
            return Response({'detail': _('Your password was changed')},
                            status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
