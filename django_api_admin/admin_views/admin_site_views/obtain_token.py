from django.utils.translation import gettext_lazy as _

from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from rest_framework_simplejwt.tokens import RefreshToken

from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse

from django_api_admin.utils.get_form_fields import get_form_fields
from django_api_admin.openapi import CommonAPIResponses, APIResponseExamples, User
from django_api_admin.serializers import FormFieldsSerializer, ObtainTokenResponseSerializer


class ObtainTokenView(APIView):
    """
    Allow users to login using username and password.
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
        }
    )
    def get(self, request):
        serializer = self.serializer_class()
        form_fields = get_form_fields(serializer)
        return Response({'fields': form_fields}, status=status.HTTP_200_OK)

    @extend_schema(
        responses={
            200: OpenApiResponse(
                description=_("Successful token obtainment"),
                response=ObtainTokenResponseSerializer,
                examples=[
                    OpenApiExample(
                        name=_("Success Response"),
                        summary=_(
                            "Example of a successful token obtain response"),
                        description=_(
                            "Returns a pair of tokens containing both the refresh and access tokens"),
                        value={
                            "detail": "you are logged in successfully",
                            "user": User,
                            "tokens": {
                                "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTczOTIyODYzMywiaWF0IjoxNzM4NjIzODMzLCJqdGkiOiI0NWFmYTUzYzk4MWY0MjdkODQ5ODgwMGRlOTNiNTY3NSIsInVzZXJfaWQiOjF9.ekHLcEXJRzuim0GlIckd4iFfSiljqfdPpIBgK2_a12s",
                                "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzM4NzEwMjMzLCJpYXQiOjE3Mzg2MjM4MzMsImp0aSI6IjkxNjljOWUxNzliMDQ3MmI4NmY0MTJhYzIyOTRkZThiIiwidXNlcl9pZCI6MX0.Gwb23W-clas-K9VfmDeXRNfEBCFRpxVdMpcp3k-fpXM"
                            }
                        },
                        status_codes=["200"]
                    )
                ],
            ),
            403: CommonAPIResponses.permission_denied(),
            401: CommonAPIResponses.unauthorized()
        }
    )
    def post(self, request):
        serializer = self.serializer_class(
            data=request.data, context={'request': request})
        if serializer.is_valid():
            user = serializer.get_user()
            tokens = self.get_tokens_for_user(user)
            user_serializer = self.admin_site.user_serializer(user)
            data = {
                'detail': _('you are logged in successfully'),
                'user': user_serializer.data,
                'tokens': tokens
            }
            return Response(data, status=status.HTTP_200_OK)

        for error in serializer.errors.get('non_field_errors', []):
            if error.code == 'permission_denied':
                return Response(serializer.errors, status=status.HTTP_403_FORBIDDEN)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_tokens_for_user(self, user):
        refresh = RefreshToken.for_user(user)
        return {
            'refresh': str(refresh),
            'access': str(refresh.access_token),
        }
