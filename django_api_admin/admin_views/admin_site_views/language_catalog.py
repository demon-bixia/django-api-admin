
from django.utils.translation import gettext_lazy as _
import json

from django.views.i18n import JSONCatalog

from rest_framework.response import Response
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample

from django_api_admin.serializers import LanguageCatalogSerializer
from django_api_admin.openapi import CommonAPIResponses


class LanguageCatalogView(APIView):
    """
      Returns json object with i18n translation catalog
      to be used by a client site javascript library
    """
    permission_classes = []
    admin_site = None

    @extend_schema(
        responses={
            200: OpenApiResponse(
                response=LanguageCatalogSerializer,
                description=_("Successful retrieval of the language catalog."),
                examples=[
                    OpenApiExample(
                        name=_("Success Response"),
                        summary=_(
                            "Example of a successful language catalog request"),
                        description=_(
                            "return the translation string used in this app"),
                        value={
                            "catalog": {
                                "AM": "ص",
                                "PM": "م",
                                "January": "يناير",
                                "February": "فبراير"
                            },
                            "formats": {
                                "DATE_FORMAT": "j F، Y",
                                "DATETIME_FORMAT": "N j, Y, P",
                                "TIME_FORMAT": "g:i A",
                                "YEAR_MONTH_FORMAT": "F Y",
                                "MONTH_DAY_FORMAT": "j F",
                                "SHORT_DATE_FORMAT": "d/m/Y",
                                "SHORT_DATETIME_FORMAT": "m/d/Y P",
                                "FIRST_DAY_OF_WEEK": 0,
                                "DECIMAL_SEPARATOR": ",",
                                "THOUSAND_SEPARATOR": ".",
                                "NUMBER_GROUPING": 0,
                                "DATE_INPUT_FORMATS": [
                                    "%Y-%m-%d",
                                    "%m/%d/%Y",
                                    "%m/%d/%y",
                                    "%b %d %Y",
                                    "%b %d, %Y",
                                    "%d %b %Y",
                                    "%d %b, %Y",
                                    "%B %d %Y",
                                    "%B %d, %Y",
                                    "%d %B %Y",
                                    "%d %B, %Y"
                                ],
                                "TIME_INPUT_FORMATS": [
                                    "%H:%M:%S",
                                    "%H:%M:%S.%f",
                                    "%H:%M"
                                ],
                                "DATETIME_INPUT_FORMATS": [
                                    "%Y-%m-%d %H:%M:%S",
                                    "%Y-%m-%d %H:%M:%S.%f",
                                    "%Y-%m-%d %H:%M",
                                    "%m/%d/%Y %H:%M:%S",
                                    "%m/%d/%Y %H:%M:%S.%f",
                                    "%m/%d/%Y %H:%M",
                                    "%m/%d/%y %H:%M:%S",
                                    "%m/%d/%y %H:%M:%S.%f",
                                    "%m/%d/%y %H:%M"
                                ]
                            },
                            "plural": "n==0 ? 0 : n==1 ? 1 : n==2 ? 2 : n%100>=3 && n%100<=10 ? 3 : n%100>=11 && n%100<=99 ? 4 : 5",
                        },
                        status_codes=["200"],
                    )
                ]
            ),
            403: CommonAPIResponses.permission_denied(),
            401: CommonAPIResponses.unauthorized(),
        }
    )
    def get(self, request):
        response = JSONCatalog.as_view(
            packages=['django_api_admin'], domain='django')(request)
        return Response(json.loads(response.content), status=response.status_code)
