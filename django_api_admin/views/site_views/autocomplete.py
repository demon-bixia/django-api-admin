from django.apps import apps
from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import FieldDoesNotExist
from django.utils.text import smart_split, unescape_string_literal

from rest_framework.exceptions import PermissionDenied, ParseError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from django_api_admin.utils.lookup_spawns_duplicates import lookup_spawns_duplicates


class AutoCompleteView(APIView):
    """
    Return a JsonResponse with search results as defined in
    serialize_result(), by default:
    {
        results: [{id: "123" text: "foo"}],
        pagination: {more: true}
    }
    """
    permission_classes = []
    admin_site = None

    def get(self, request):
        """
        Return a JsonResponse with search results as defined in
        serialize_result(), by default:
        {
            results: [{id: "123" text: "foo"}],
            pagination: {more: true}
        }
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
        """Return queryset based on self.get_search_results()."""
        qs = self.model_admin.get_queryset()
        qs = qs.complex_filter(self.source_field.get_limit_choices_to())
        qs, search_use_distinct = self.get_search_results(
            self.request, qs, self.term)
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
                {'detail': 'missing values app_label, model_name, and field_name'})

        # Retrieve objects from parameters.
        try:
            source_model = apps.get_model(app_label, model_name)
        except LookupError:
            raise ParseError({'detail': 'source model not found'})
        try:
            source_field = source_model._meta.get_field(field_name)
        except FieldDoesNotExist:
            raise ParseError(
                {f'detail': 'source field not found in source model {source_model._meta.verbose_name}'})
        try:
            remote_model = source_field.remote_field.model
        except AttributeError:
            raise ParseError(
                {'detail': 'unable to locate the related model using source field {source_field.name}'})
        try:
            model_admin = self.admin_site._registry[remote_model]
        except KeyError:
            raise ParseError(
                {'detail': 'the remote model is not registered in the admin'})

        # Validate suitability of objects.
        if not getattr(model_admin, "search_fields"):
            raise ParseError(f'{type(
                model_admin).__qualname__} must have search_fields for the autocomplete_view."')

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

    def get_search_results(self, request, queryset, search_term):
        """
        Return a tuple containing a queryset to implement the search
        and a boolean indicating if the results may contain duplicates.
        """
        # Apply keyword searches.
        def construct_search(field_name):
            if field_name.startswith("^"):
                return "%s__istartswith" % field_name[1:]
            elif field_name.startswith("="):
                return "%s__iexact" % field_name[1:]
            elif field_name.startswith("@"):
                return "%s__search" % field_name[1:]
            # Use field_name if it includes a lookup.
            opts = queryset.model._meta
            lookup_fields = field_name.split("__")
            # Go through the fields, following all relations.
            prev_field = None
            for path_part in lookup_fields:
                if path_part == "pk":
                    path_part = opts.pk.name
                try:
                    field = opts.get_field(path_part)
                except FieldDoesNotExist:
                    # Use valid query lookups.
                    if prev_field and prev_field.get_lookup(path_part):
                        return field_name
                else:
                    prev_field = field
                    if hasattr(field, "path_infos"):
                        # Update opts to follow the relation.
                        opts = field.path_infos[-1].to_opts
            # Otherwise, use the field with icontains.
            return "%s__icontains" % field_name

        may_have_duplicates = False
        search_fields = self.model_admin.search_fields
        if search_fields and search_term:
            orm_lookups = [
                construct_search(str(search_field)) for search_field in search_fields
            ]
            term_queries = []
            for bit in smart_split(search_term):
                if bit.startswith(('"', "'")) and bit[0] == bit[-1]:
                    bit = unescape_string_literal(bit)
                or_queries = Q.create(
                    [(orm_lookup, bit) for orm_lookup in orm_lookups],
                    connector=Q.OR,
                )
                term_queries.append(or_queries)
            queryset = queryset.filter(Q.create(term_queries))
            may_have_duplicates |= any(
                lookup_spawns_duplicates(self.model_admin.opts, search_spec)
                for search_spec in orm_lookups
            )
        return queryset, may_have_duplicates
