from datetime import datetime, timedelta

from django.conf import settings
from django.core.exceptions import FieldDoesNotExist, ImproperlyConfigured, SuspiciousOperation
from django.core.paginator import InvalidPage
from django.db.models import Exists, F, Field, ManyToOneRel, OrderBy, OuterRef
from django.utils.timezone import make_aware
from django.utils.http import urlencode

from django_api_admin.exceptions import DisallowedModelAdminLookup, IncorrectLookupParameters
from django_api_admin.filters import FieldListFilter
from django_api_admin.serializers import ChangeListSerializer
from django_api_admin.utils.get_fields_from_path import get_fields_from_path
from django_api_admin.utils.lookup_spawns_duplicates import lookup_spawns_duplicates
from django_api_admin.utils.prepare_lookup_value import prepare_lookup_value
from django_api_admin.constants.vars import TO_FIELD_VAR, IS_POPUP_VAR, ALL_VAR, ORDER_VAR, SEARCH_VAR, PAGE_VAR, ERROR_FLAG


class ChangeList:
    serializer_class = ChangeListSerializer

    def __init__(
        self,
        request,
        model,
        list_display,
        list_display_links,
        list_filter,
        date_hierarchy,
        search_fields,
        list_select_related,
        list_per_page,
        list_max_show_all,
        list_editable,
        model_admin,
        sortable_by,
        search_help_text,
    ):
        self.model = model
        self.opts = model._meta
        self.lookup_opts = self.opts
        self.root_queryset = model_admin.get_queryset(request)
        self.list_display = list_display
        self.list_display_links = list_display_links
        self.list_filter = list_filter
        self.list_editable = list_editable
        self.has_filters = None
        self.has_active_filters = None
        self.clear_all_filters_qs = None
        self.date_hierarchy = date_hierarchy
        self.search_fields = search_fields
        self.list_select_related = list_select_related
        self.list_per_page = list_per_page
        self.list_max_show_all = list_max_show_all
        self.model_admin = model_admin
        self.preserved_filters = model_admin.get_preserved_filters(request)
        self.sortable_by = sortable_by
        self.search_help_text = search_help_text

        search_serializer = self.serializer_class(data=request.GET)
        if not search_serializer.is_valid():
            errors = [
                {'detail': ", ".join(error)}
                for error in search_serializer.errors.values()
            ]
            raise IncorrectLookupParameters(errors)
        self.query = search_serializer.validated_data.get(SEARCH_VAR) or ""

        try:
            self.page_num = int(request.GET.get(PAGE_VAR, 1))
        except ValueError:
            self.page_num = 1

        self.show_all = "all" in request.GET
        self.params = dict(request.GET.items())
        if PAGE_VAR in self.params:
            del self.params[PAGE_VAR]
        if ERROR_FLAG in self.params:
            del self.params[ERROR_FLAG]

        self.root_queryset = model_admin.get_queryset(request)
        self.queryset = self.get_queryset(request)
        self.get_results()

    def __repr__(self):
        return "<%s: model=%s model_admin=%s>" % (
            self.__class__.__qualname__,
            self.model.__qualname__,
            self.model_admin.__class__.__qualname__,
        )

    def get_filters_params(self, params=None):
        """
        Return all params except IGNORED_PARAMS.
        """
        params = params or self.params
        lookup_params = params.copy()  # a dictionary of the query string
        # Remove all the parameters that are globally and systematically
        # ignored.
        for ignored in (ALL_VAR, ORDER_VAR, SEARCH_VAR, IS_POPUP_VAR, TO_FIELD_VAR):
            if ignored in lookup_params:
                del lookup_params[ignored]
        return lookup_params

    def get_filters(self, request):
        lookup_params = self.get_filters_params()
        may_have_duplicates = False
        has_active_filters = False

        for key, value in lookup_params.items():
            if not self.model_admin.lookup_allowed(key, value):
                raise DisallowedModelAdminLookup(
                    f"Filtering by {key} not allowed")

        filter_specs = []
        for list_filter in self.list_filter:
            lookup_params_count = len(lookup_params)
            if callable(list_filter):
                # This is simply a custom list filter class.
                spec = list_filter(request, lookup_params,
                                   self.model, self.model_admin)
            else:
                field_path = None
                if isinstance(list_filter, (tuple, list)):
                    # This is a custom FieldListFilter class for a given field.
                    field, field_list_filter_class = list_filter
                else:
                    # This is simply a field name, so use the default
                    # FieldListFilter class that has been registered for the
                    # type of the given field.
                    field, field_list_filter_class = list_filter, FieldListFilter.create
                if not isinstance(field, Field):
                    field_path = field
                    field = get_fields_from_path(self.model, field_path)[-1]

                spec = field_list_filter_class(
                    field,
                    request,
                    lookup_params,
                    self.model,
                    self.model_admin,
                    field_path=field_path,
                )
                # field_list_filter_class removes any lookup_params it
                # processes. If that happened, check if duplicates should be
                # removed.
                if lookup_params_count > len(lookup_params):
                    may_have_duplicates |= lookup_spawns_duplicates(
                        self.opts,
                        field_path,
                    )
            if spec and spec.has_output():
                filter_specs.append(spec)
                if lookup_params_count > len(lookup_params):
                    has_active_filters = True

        if self.date_hierarchy:
            # Create bounded lookup parameters so that the query is more
            # efficient.
            year = lookup_params.pop("%s__year" % self.date_hierarchy, None)
            if year is not None:
                month = lookup_params.pop(
                    "%s__month" % self.date_hierarchy, None)
                day = lookup_params.pop("%s__day" % self.date_hierarchy, None)
                try:
                    from_date = datetime(
                        int(year),
                        int(month if month is not None else 1),
                        int(day if day is not None else 1),
                    )
                except ValueError as e:
                    raise IncorrectLookupParameters(e) from e
                if day:
                    to_date = from_date + timedelta(days=1)
                elif month:
                    # In this branch, from_date will always be the first of a
                    # month, so advancing 32 days gives the next month.
                    to_date = (from_date + timedelta(days=32)).replace(day=1)
                else:
                    to_date = from_date.replace(year=from_date.year + 1)
                if settings.USE_TZ:
                    from_date = make_aware(from_date)
                    to_date = make_aware(to_date)
                lookup_params.update(
                    {
                        "%s__gte" % self.date_hierarchy: from_date,
                        "%s__lt" % self.date_hierarchy: to_date,
                    }
                )

        # At this point, all the parameters used by the various ListFilters
        # have been removed from lookup_params, which now only contains other
        # parameters passed via the query string. We now loop through the
        # remaining parameters both to ensure that all the parameters are valid
        # fields and to determine if at least one of them spawns duplicates. If
        # the lookup parameters aren't real fields, then bail out.
        try:
            for key, value in lookup_params.items():
                lookup_params[key] = prepare_lookup_value(key, value)
                may_have_duplicates |= lookup_spawns_duplicates(
                    self.opts, key)
            return (
                filter_specs,
                bool(filter_specs),
                lookup_params,
                may_have_duplicates,
                has_active_filters,
            )
        except FieldDoesNotExist as e:
            raise IncorrectLookupParameters(e) from e

    def get_query_string(self, new_params=None, remove=None):
        if new_params is None:
            new_params = {}
        if remove is None:
            remove = []
        p = self.params.copy()
        for r in remove:
            for k in list(p):
                if k.startswith(r):
                    del p[k]
        for k, v in new_params.items():
            if v is None:
                if k in p:
                    del p[k]
            else:
                p[k] = v
        return "?%s" % urlencode(sorted(p.items()))

    def get_results(self):
        paginator = self.model_admin.get_paginator(
            self.queryset, self.list_per_page
        )
        # Get the number of objects, with admin filters applied.
        result_count = paginator.count

        # Get the total number of objects, with no admin filters applied.
        if self.model_admin.show_full_result_count:
            full_result_count = self.root_queryset.count()
        else:
            full_result_count = None
        can_show_all = result_count <= self.list_max_show_all
        multi_page = result_count > self.list_per_page

        # Get the list of objects to display on this page.
        if (self.show_all and can_show_all) or not multi_page:
            result_list = self.queryset._clone()
        else:
            try:
                result_list = paginator.page(self.page_num).object_list
            except InvalidPage:
                raise IncorrectLookupParameters

        self.result_count = result_count
        self.show_full_result_count = self.model_admin.show_full_result_count
        # Admin actions are shown if there is at least one entry
        # or if entries are not counted because show_full_result_count is disabled
        self.show_admin_actions = not self.show_full_result_count or bool(
            full_result_count
        )
        self.full_result_count = full_result_count
        self.result_list = result_list
        self.can_show_all = can_show_all
        self.multi_page = multi_page
        self.paginator = paginator

    def get_ordering(self, queryset):
        """
        Return the list of ordering fields for the change list.
        First check the get_ordering() method in model admin, then check
        the object's default ordering. Then, any manually-specified ordering
        from the query string overrides anything. Finally, a deterministic
        order is guaranteed by calling _get_deterministic_ordering() with the
        constructed ordering.
        """
        params = self.params
        ordering = list(self._get_default_ordering())
        if "o" in params:
            # Clear ordering and used params
            ordering = []
            order_params = params["o"].split(".")
            for p in order_params:
                try:
                    none, pfx, idx = p.rpartition("-")
                    field_name = self.list_display[int(idx)]
                    order_field = self.get_ordering_field(field_name)
                    if not order_field:
                        continue  # No 'admin_order_field', skip it
                    if isinstance(order_field, OrderBy):
                        if pfx == "-":
                            order_field = order_field.copy()
                            order_field.reverse_ordering()
                        ordering.append(order_field)
                    elif hasattr(order_field, "resolve_expression"):
                        # order_field is an expression.
                        ordering.append(
                            order_field.desc() if pfx == "-" else order_field.asc()
                        )
                    # reverse order if order_field has already "-" as prefix
                    elif order_field.startswith("-") and pfx == "-":
                        ordering.append(order_field[1:])
                    else:
                        ordering.append(pfx + order_field)
                except (IndexError, ValueError):
                    continue  # Invalid ordering specified, skip it.

        # Add the given query's ordering fields, if any.
        ordering.extend(queryset.query.order_by)

        return self._get_deterministic_ordering(ordering)

    def _get_default_ordering(self):
        ordering = []
        if self.model_admin.ordering:
            ordering = self.model_admin.ordering
        elif self.opts.ordering:
            ordering = self.opts.ordering
        return ordering

    def get_ordering_field(self, field_name):
        """
        Return the proper model field name corresponding to the given
        field_name to use for ordering. field_name may either be the name of a
        proper model field or the name of a method (on the admin or model) or a
        callable with the 'admin_order_field' attribute. Return None if no
        proper model field name can be matched.
        """
        try:
            field = self.opts.get_field(field_name)
            return field.name
        except FieldDoesNotExist:
            # See whether field_name is a name of a non-field
            # that allows sorting.
            if callable(field_name):
                attr = field_name
            elif hasattr(self.model_admin, field_name):
                attr = getattr(self.model_admin, field_name)
            else:
                attr = getattr(self.model, field_name)
            if isinstance(attr, property) and hasattr(attr, "fget"):
                attr = attr.fget
            return getattr(attr, "admin_order_field", None)

    def _get_deterministic_ordering(self, ordering):
        """
        Ensure a deterministic order across all database backends. Search for a
        single field or unique together set of fields providing a total
        ordering. If these are missing, augment the ordering with a descendant
        primary key.
        """
        ordering = list(ordering)
        ordering_fields = set()
        total_ordering_fields = {"pk"} | {
            field.attname
            for field in self.opts.fields
            if field.unique and not field.null
        }
        for part in ordering:
            # Search for single field providing a total ordering.
            field_name = None
            if isinstance(part, str):
                field_name = part.lstrip("-")
            elif isinstance(part, F):
                field_name = part.name
            elif isinstance(part, OrderBy) and isinstance(part.expression, F):
                field_name = part.expression.name
            if field_name:
                # Normalize attname references by using get_field().
                try:
                    field = self.opts.get_field(field_name)
                except FieldDoesNotExist:
                    # Could be "?" for random ordering or a related field
                    # lookup. Skip this part of introspection for now.
                    continue
                # Ordering by a related field name orders by the referenced
                # model's ordering. Skip this part of introspection for now.
                if field.remote_field and field_name == field.name:
                    continue
                if field.attname in total_ordering_fields:
                    break
                ordering_fields.add(field.attname)
        else:
            # No single total ordering field, try unique_together and total
            # unique constraints.
            constraint_field_names = (
                *self.opts.unique_together,
                *(
                    constraint.fields
                    for constraint in self.opts.total_unique_constraints
                ),
            )
            for field_names in constraint_field_names:
                # Normalize attname references by using get_field().
                fields = [
                    self.opts.get_field(field_name) for field_name in field_names
                ]
                # Composite unique constraints containing a nullable column
                # cannot ensure total ordering.
                if any(field.null for field in fields):
                    continue
                if ordering_fields.issuperset(field.attname for field in fields):
                    break
            else:
                # If no set of unique fields is present in the ordering, rely
                # on the primary key to provide total ordering.
                ordering.append("-pk")
        return ordering

    def get_queryset(self, request):
        # First, we collect all the declared list filters.
        (
            self.filter_specs,
            self.has_filters,
            remaining_lookup_params,
            filters_may_have_duplicates,
            self.has_active_filters,
        ) = self.get_filters(request)
        # Then, we let every list filter modify the queryset to its liking.
        qs = self.root_queryset
        for filter_spec in self.filter_specs:
            new_qs = filter_spec.queryset(request, qs)
            if new_qs is not None:
                qs = new_qs

        try:
            # Finally, we apply the remaining lookup parameters from the query
            # string (i.e. those that haven't already been processed by the
            # filters).
            qs = qs.filter(**remaining_lookup_params)
        except (SuspiciousOperation, ImproperlyConfigured):
            # Allow certain types of errors to be re-raised as-is so that the
            # caller can treat them in a special way.
            raise
        except Exception as e:
            # Every other error is caught with a naked except, because we don't
            # have any other way of validating lookup parameters. They might be
            # invalid if the keyword arguments are incorrect, or if the values
            # are not in the correct type, so we might get FieldError,
            # ValueError, ValidationError, or ?.
            raise IncorrectLookupParameters(e)

        # Apply search results
        qs, search_may_have_duplicates = self.model_admin.get_search_results(
            qs,
            self.query,
        )

        # Set query string for clearing all filters.
        self.clear_all_filters_qs = self.get_query_string(
            new_params=remaining_lookup_params,
            remove=self.get_filters_params(),
        )
        # Remove duplicates from results, if necessary
        if filters_may_have_duplicates | search_may_have_duplicates:
            qs = qs.filter(pk=OuterRef("pk"))
            qs = self.root_queryset.filter(Exists(qs))

        # Set ordering.
        ordering = self.get_ordering(qs)
        qs = qs.order_by(*ordering)

        if not qs.query.select_related:
            qs = self.apply_select_related(qs)

        return qs

    def apply_select_related(self, qs):
        if self.list_select_related is True:
            return qs.select_related()

        if self.list_select_related is False:
            if self.has_related_field_in_list_display():
                return qs.select_related()

        if self.list_select_related:
            return qs.select_related(*self.list_select_related)
        return qs

    def has_related_field_in_list_display(self):
        for field_name in self.list_display:
            try:
                field = self.opts.get_field(field_name)
            except FieldDoesNotExist:
                pass
            else:
                if isinstance(field.remote_field, ManyToOneRel):
                    # <FK>_id field names don't require a join.
                    if field_name != field.get_attname():
                        return True
        return False
