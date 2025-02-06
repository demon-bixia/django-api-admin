from django.apps import apps
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import FieldDoesNotExist

from rest_framework.exceptions import PermissionDenied, ParseError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema, OpenApiExample, OpenApiResponse

from django_api_admin.serializers import AutoCompleteSerializer
from django_api_admin.openapi import CommonAPIResponses


class AutoCompleteView(APIView):
    """
    API view for handling autocomplete functionality in admin fields.
    """
    permission_classes = []
    admin_site = None

    @extend_schema(
        parameters=[AutoCompleteSerializer],
        responses={
            200: OpenApiResponse(
                description=_("Successful autocomplete response"),
                response=AutoCompleteSerializer,
                examples=[
                    OpenApiExample(
                        name=_("Success Response"),
                        summary=_(
                            "Example of a successful autocomplete response"),
                        description="Returns matching records based on the search term",
                        value=[{
                            "id": 1,
                            "name": "Muhammad",
                            "age": 60,
                            "is_vip": True,
                            "date_joined": "2025-02-02T23:09:31.994853Z",
                            "title": None,
                            "user": 1,
                            "publisher": [1],
                            "pk": 1
                        }],
                        status_codes=["200"],
                    )
                ]
            ),
            403: CommonAPIResponses.permission_denied(),
            401: CommonAPIResponses.unauthorized(),
        },
        description=_(
            "Endpoint for autocomplete functionality on model fields")
    )
    def get(self, request):
        """
        Process the request to extract search parameters,
        validates user permissions, retrieves the relevant queryset,
        paginates the results, and returns them as a JSON response.
        """
        (
            self.term,
            self.model_admin,
            self.source_field,
            to_field_name,
        ) = self.process_request(request)

        if not self.has_perm(request):
            raise PermissionDenied

        self.queryset = self.get_queryset()
        page = self.admin_site.paginate_queryset(
            self.queryset, request, view=self)

        # serialize data
        serializer_class = self.model_admin.get_serializer_class()
        serializer = serializer_class(page, many=True)
        data = serializer.data

        return Response(
            data,
            status=status.HTTP_200_OK
        )

    def get_queryset(self):
        """Return queryset based on model_admin.get_search_results()."""
        qs = self.model_admin.get_queryset()
        qs = qs.complex_filter(self.source_field.get_limit_choices_to())
        qs, search_use_distinct = self.model_admin.get_search_results(
            qs, self.term)
        if search_use_distinct:
            qs = qs.distinct()
        return qs

    def process_request(self, request):
        """
        Validate request integrity, extract and return request parameters.

        Since the subsequent view permission check requires the target model
        admin, which is determined here, raise PermissionDenied if the
        requested app, model or field are malformed.

        Raise Http404 if the target model admin is not configured properly with
        search_fields.
        """
        term = request.GET.get("term", "")

        try:
            app_label = request.GET["app_label"]
            model_name = request.GET["model_name"]
            field_name = request.GET["field_name"]
        except KeyError:
            raise ParseError(
                {'detail': _('missing values app_label, model_name, and field_name')})

        # Retrieve objects from parameters.
        try:
            source_model = apps.get_model(app_label, model_name)
        except LookupError:
            raise ParseError({'detail': _('source model not found')})
        try:
            source_field = source_model._meta.get_field(field_name)
        except FieldDoesNotExist:
            raise ParseError(
                {f'detail': _(f'source field not found in source model {source_model._meta.verbose_name}')})
        try:
            remote_model = source_field.remote_field.model
        except AttributeError:
            raise ParseError(
                {'detail': _(f'unable to locate the related model using source field {source_field.name}')})
        try:
            model_admin = self.admin_site._registry[remote_model]
        except KeyError:
            raise ParseError(
                {'detail': _('the remote model is not registered in the admin')})

        # Validate suitability of objects.
        if not getattr(model_admin, "search_fields"):
            raise ParseError(_('%s must have search_fields for the autocomplete_view."') % type(
                model_admin).__qualname__)

        to_field_name = getattr(
            source_field.remote_field, "field_name", remote_model._meta.pk.attname
        )
        to_field_name = remote_model._meta.get_field(to_field_name).attname
        if not model_admin.to_field_allowed(to_field_name):
            raise PermissionDenied

        return term, model_admin, source_field, to_field_name

    def has_perm(self, request):
        """Check if user has permission to access the related model."""
        return self.model_admin.has_view_permission(request)
