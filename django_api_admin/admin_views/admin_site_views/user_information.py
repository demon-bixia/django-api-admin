from django.utils.translation import gettext_lazy as _

from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample

from django_api_admin.openapi import User, CommonAPIResponses
from django_api_admin.serializers import UserSerializer


class UserInformation(APIView):
    serializer_class = None
    permission_classes = []
    admin_site = None

    @extend_schema(
        responses={
            200: OpenApiResponse(
                description=_("Successful retrieval of user information"),
                response=UserSerializer,
                examples=[
                    OpenApiExample(
                        name=_("User Information"),
                        summary=_(
                            "Example of a successful user information retrieval response"),
                        description=_(
                            "Returns details of the user's information"),
                        value=User,
                        status_codes=["200"]
                    )
                ],
            ),
            403: CommonAPIResponses.permission_denied(),
            401: CommonAPIResponses.unauthorized()
        }
    )
    def get(self, request):
        serializer = self.serializer_class(request.user)
        return Response({'user': serializer.data})
