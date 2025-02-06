from django.core.exceptions import FieldDoesNotExist, ValidationError
from django.core.paginator import Paginator
from django.db import models
from django.urls import include, path
from django.utils.http import urlencode
from django.utils.safestring import mark_safe
from django.utils.text import capfirst, smart_split, unescape_string_literal

from rest_framework import serializers

from django_api_admin.filters import SimpleListFilter
from django_api_admin.admins.base_admin import BaseAPIModelAdmin
from django_api_admin.utils.get_content_type_for_model import get_content_type_for_model
from django_api_admin.utils.lookup_spawns_duplicates import lookup_spawns_duplicates
from django_api_admin.utils.model_format_dict import model_format_dict
from django_api_admin.utils.url_params_from_lookup_dict import url_params_from_lookup_dict
from django_api_admin.checks import APIModelAdminChecks
from django_api_admin.constants.vars import LOOKUP_SEP


class APIModelAdmin(BaseAPIModelAdmin):
    """
    provides a restful version of django.contrib.admin.options.ModelAdmin.
    everything that is ui specific is handled by the ui
    filtering is also handled by the ui
    """
    list_display = ("__str__",)
    list_display_links = ()
    list_filter = ()
    list_select_related = False
    list_per_page = 100
    list_max_show_all = 200
    list_editable = ()
    search_fields = ()
    search_help_text = None
    date_hierarchy = None
    save_as = False
    save_as_continue = True
    save_on_top = False
    paginator = Paginator
    action_serializer = None
    preserve_filters = True
    inlines = ()
    actions = ()
    actions_on_top = True
    actions_on_bottom = False
    actions_selection_counter = True
    checks_class = APIModelAdminChecks

    # these are the admin options used to customize the change list page interface
    # server-side customizations like list_select_related and actions are not included
    changelist_options = [
        # actions options
        'actions_on_top', 'actions_on_bottom', 'actions_selection_counter',
        # display options
        'empty_value_display', 'list_display', 'list_display_links', 'list_editable',
        'exclude',
        # pagination
        'show_full_result_count', 'list_per_page', 'list_max_show_all',
        # filtering, sorting and searching
        'date_hierarchy', 'search_help_text', 'sortable_by', 'search_fields',
        'preserve_filters',
    ]

    def __init__(self, model, admin_site):
        self.model = model
        self.opts = model._meta
        self.admin_site = admin_site
        self.view_on_site = False if not self.admin_site.include_view_on_site_view else self.view_on_site

    def get_model_perms(self, request):
        """
        Return a dict of all perms for this model. This dict has the keys
        ``add``, ``change``, ``delete``, and ``view`` mapping to the True/False
        for each of those actions.
        """
        return {
            "add": self.has_add_permission(request),
            "change": self.has_change_permission(request),
            "delete": self.has_delete_permission(request),
            "view": self.has_view_permission(request),
        }

    def get_action_serializer(self, request):
        from django_api_admin.serializers import ActionSerializer

        if self.action_serializer:
            return self.action_serializer

        self.action_serializer = type(f'{self.model.__name__}ActionSerializer', (ActionSerializer,), {
            'action': serializers.ChoiceField(choices=[*self.get_action_choices(request)]),
            'selected_ids': serializers.MultipleChoiceField(choices=[*self.get_selected_ids()])
        })
        return self.action_serializer

    def get_paginator(self, queryset, per_page, orphans=0, allow_empty_first_page=True):
        return self.paginator(queryset, per_page, orphans, allow_empty_first_page)

    def get_selected_ids(self):
        queryset = self.get_queryset()
        choices = []
        for item in queryset:
            choices.append((f'{item.pk}', f'{str(item)}'))
        return choices

    def get_inline_instances(self, request):
        inline_instances = []
        for inline_class in self.inlines:
            inline = inline_class(self.model, self.admin_site)
            if request:
                if not (
                    inline.has_view_or_change_permission(request)
                    or inline.has_add_permission(request)
                    or inline.has_delete_permission(request)
                ):
                    continue
                if not inline.has_add_permission(request):
                    inline.max_num = 0
            inline_instances.append(inline)

        return inline_instances

    def get_changelist_instance(self, request):
        """
        Return a `ChangeList` instance based on `request`. May raise
        `IncorrectLookupParameters`.
        """
        from django_api_admin.changelist import ChangeList

        list_display = self.list_display
        list_display_links = self.get_list_display_links(list_display)
        # Add the action checkboxes if any actions are available.
        if self.get_actions(request):
            list_display = ["action_checkbox", *list_display]
        sortable_by = self.get_sortable_by()
        return ChangeList(
            request,
            self.model,
            list_display,
            list_display_links,
            self.list_filter,
            self.date_hierarchy,
            self.search_fields,
            self.list_select_related,
            self.list_per_page,
            self.list_max_show_all,
            self.list_editable,
            self,
            sortable_by,
            self.search_help_text
        )

    def get_object(self, request, object_id, from_field=None):
        """
        Return an instance matching the field and value provided, the primary
        key is used if no field is provided. Return ``None`` if no match is
        found or the object_id fails validation.
        """
        queryset = self.get_queryset(request)
        model = queryset.model
        field = (
            model._meta.pk if from_field is None else model._meta.get_field(
                from_field)
        )
        try:
            object_id = field.to_python(object_id)
            return queryset.get(**{field.name: object_id})
        except (model.DoesNotExist, ValidationError, ValueError):
            return None

    def get_empty_value_display(self):
        """
        Return the empty_value_display set on ModelAdmin or AdminSite.
        """
        try:
            return mark_safe(self.empty_value_display)
        except AttributeError:
            return mark_safe(self.admin_site.empty_value_display)

    def get_sortable_by(self):
        """Hook for specifying which fields can be sorted in the changelist."""
        return (
            self.sortable_by
            if self.sortable_by is not None
            else self.list_display
        )

    def get_action_choices(self, request, default_choices=models.BLANK_CHOICE_DASH):
        """
        Return a list of choices for use in a form object.  Each choice is a
        tuple (name, description).
        """
        choices = [] + default_choices
        for func, name, description in self.get_actions(request).values():
            choice = (name, description % model_format_dict(self.opts, models))
            choices.append(choice)
        return choices

    def get_actions(self, request):
        """
        Return a dictionary mapping the names of all actions for this
        ModelAdmin to a tuple of (callable, name, description) for each action.
        """
        # If self.actions is set to None that means actions are disabled on
        # this page.
        if self.actions is None:
            return {}
        actions = self._filter_actions_by_permissions(
            request, self._get_base_actions())
        return {name: (func, name, desc) for func, name, desc in actions}

    def get_action(self, action):
        """
        Return a given action from a parameter, which can either be a callable,
        or the name of a method on the ModelAdmin.  Return is a tuple of
        (callable, name, description).
        """
        # If the action is a callable, just use it.
        if callable(action):
            func = action
            action = action.__name__

        # Next, look for a method. Grab it off self.__class__ to get an unbound
        # method instead of a bound one; this ensures that the calling
        # conventions are the same for functions and methods.
        elif hasattr(self.__class__, action):
            func = getattr(self.__class__, action)

        # Finally, look for a named method on the admin site
        else:
            try:
                func = self.admin_site.get_action(action)
            except KeyError:
                return None

        description = getattr(func, "short_description",
                              capfirst(action.replace("_", " ")))
        return func, action, description

    def get_list_display(self):
        """
        Return a sequence containing the fields to be displayed on the
        changelist.
        """
        return self.list_display

    def get_list_display_links(self, list_display):
        """
        Return a sequence containing the fields to be displayed as links
        on the changelist. The list_display parameter is the list of fields
        returned by get_list_display().
        """
        if (
            self.list_display_links
            or self.list_display_links is None
            or not list_display
        ):
            return self.list_display_links
        else:
            # Use only the first item in list_display as link
            return list(list_display)[:1]

    def _filter_actions_by_permissions(self, request, actions):
        """Filter out any actions that the user doesn't have access to."""
        filtered_actions = []
        for action in actions:
            callable = action[0]
            if not hasattr(callable, "allowed_permissions"):
                filtered_actions.append(action)
                continue
            permission_checks = (
                getattr(self, "has_%s_permission" % permission)
                for permission in callable.allowed_permissions
            )
            if any(has_permission(request) for has_permission in permission_checks):
                filtered_actions.append(action)
        return filtered_actions

    def _get_base_actions(self):
        """Return the list of actions, prior to any request-based filtering."""
        actions = []
        base_actions = (self.get_action(action)
                        for action in self.actions or [])
        # get_action might have returned None, so filter any of those out.
        base_actions = [action for action in base_actions if action]
        base_action_names = {name for _, name, _ in base_actions}

        # Gather actions from the admin site first
        for name, func in self.admin_site.actions:
            if name in base_action_names:
                continue
            description = getattr(func, "short_description",
                                  capfirst(name.replace("_", " ")))
            actions.append((func, name, description))

        # Add actions from this ModelAdmin.
        actions.extend(base_actions)
        return actions

    def get_urls(self):
        info = self.model._meta.app_label, self.model._meta.model_name
        prefix = f'{self.model._meta.app_label}/{self.model._meta.model_name}'
        urlpatterns = [
            path(f'{prefix}/list/', self.get_list_view(),
                 name='%s_%s_list' % info),
            path(f'{prefix}/changelist/', self.get_changelist_view(),
                 name='%s_%s_changelist' % info),
            path(f'{prefix}/perform_action/', self.get_handle_action_view(),
                 name='%s_%s_perform_action' % info),
            path(f'{prefix}/add/', self.get_add_view(),
                 name='%s_%s_add' % info),
            path(f'{prefix}/<path:object_id>/detail/', self.get_detail_view(),
                 name='%s_%s_detail' % info),
            path(f'{prefix}/<path:object_id>/delete/', self.get_delete_view(),
                 name='%s_%s_delete' % info),
            path(f'{prefix}/<path:object_id>/history/',
                 self.get_history_view(), name='%s_%s_history' % info),
            path(f'{prefix}/<path:object_id>/change/', self.get_change_view(),
                 name='%s_%s_change' % info),
        ]

        # add Inline admins urls
        for inline_class in self.inlines:
            inline = inline_class(self.model, self.admin_site)
            urlpatterns += inline.urls
        return urlpatterns

    @property
    def urls(self):
        return self.get_urls()

    def to_field_allowed(self, to_field):
        """
        Return True if the model associated with this admin should be
        allowed to be referenced by the specified field.
        """
        try:
            field = self.opts.get_field(to_field)
        except FieldDoesNotExist:
            return False

        # Always allow referencing the primary key since it's already possible
        # to get this information from the change view URL.
        if field.primary_key:
            return True

        # Allow reverse relationships to models defining m2m fields if they
        # target the specified field.
        for many_to_many in self.opts.many_to_many:
            if many_to_many.m2m_target_field_name() == to_field:
                return True

        # Make sure at least one of the models registered for this site
        # references this field through a FK or a M2M relationship.
        registered_models = set()
        for model, admin in self.admin_site._registry.items():
            registered_models.add(model)
            for inline in admin.inlines:
                registered_models.add(inline.model)

        related_objects = (
            f
            for f in self.opts.get_fields(include_hidden=True)
            if (f.auto_created and not f.concrete)
        )
        for related_object in related_objects:
            related_model = related_object.related_model
            remote_field = related_object.field.remote_field
            if (
                any(issubclass(model, related_model)
                    for model in registered_models)
                and hasattr(remote_field, "get_related_field")
                and remote_field.get_related_field() == field
            ):
                return True

        return False

    def lookup_allowed(self, lookup, value):
        model = self.model
        # Check FKey lookups that are allowed, so that popups produced by
        # ForeignKeyRawIdWidget, on the basis of ForeignKey.limit_choices_to,
        # are allowed to work.
        for fk_lookup in model._meta.related_fkey_lookups:
            # As ``limit_choices_to`` can be a callable, invoke it here.
            if callable(fk_lookup):
                fk_lookup = fk_lookup()
            if (lookup, value) in url_params_from_lookup_dict(
                fk_lookup
            ).items():
                return True

        relation_parts = []
        prev_field = None
        for part in lookup.split(LOOKUP_SEP):
            try:
                field = model._meta.get_field(part)
            except FieldDoesNotExist:
                # Lookups on nonexistent fields are ok, since they're ignored
                # later.
                break
            # It is allowed to filter on values that would be found from local
            # model anyways. For example, if you filter on employee__department__id,
            # then the id value would be found already from employee__department_id.
            if not prev_field or (
                prev_field.is_relation
                and field not in prev_field.path_infos[-1].target_fields
            ):
                relation_parts.append(part)
            if not getattr(field, "path_infos", None):
                # This is not a relational field, so further parts
                # must be transforms.
                break
            prev_field = field
            model = field.path_infos[-1].to_opts.model

        if len(relation_parts) <= 1:
            # Either a local field filter, or no fields at all.
            return True
        valid_lookups = {self.date_hierarchy}
        for filter_item in self.list_filter:
            if isinstance(filter_item, type) and issubclass(
                filter_item, SimpleListFilter
            ):
                valid_lookups.add(filter_item.parameter_name)
            elif isinstance(filter_item, (list, tuple)):
                valid_lookups.add(filter_item[0])
            else:
                valid_lookups.add(filter_item)

        # Is it a valid relational lookup?
        return not {
            LOOKUP_SEP.join(relation_parts),
            LOOKUP_SEP.join(relation_parts + [part]),
        }.isdisjoint(valid_lookups)

    def get_changelist_view(self):
        from django_api_admin.admin_views.model_admin_views.changelist import ChangeListView

        defaults = {
            'permission_classes': self.admin_site.default_permission_classes,
            'authentication_classes': self.admin_site.authentication_classes,
            'model_admin': self
        }
        return ChangeListView.as_view(**defaults)

    def get_handle_action_view(self):
        from django_api_admin.admin_views.model_admin_views.handle_action import HandleActionView

        defaults = {
            'permission_classes': self.admin_site.default_permission_classes,
            'authentication_classes': self.admin_site.authentication_classes,
            'model_admin': self
        }
        return HandleActionView.as_view(**defaults)

    def get_history_view(self):
        from django_api_admin.admin_views.model_admin_views.history import HistoryView

        defaults = {
            'permission_classes': self.admin_site.default_permission_classes,
            'serializer_class': self.admin_site.log_entry_serializer,
            'authentication_classes': self.admin_site.authentication_classes,
            'model_admin': self
        }
        return HistoryView.as_view(**defaults)

    def get_search_results(self, queryset, search_term):
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
            lookup_fields = field_name.split(LOOKUP_SEP)
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
        search_fields = self.search_fields
        if search_fields and search_term:
            orm_lookups = [
                construct_search(str(search_field)) for search_field in search_fields
            ]
            term_queries = []
            for bit in smart_split(search_term):
                if bit.startswith(('"', "'")) and bit[0] == bit[-1]:
                    bit = unescape_string_literal(bit)
                or_queries = models.Q.create(
                    [(orm_lookup, bit) for orm_lookup in orm_lookups],
                    connector=models.Q.OR,
                )
                term_queries.append(or_queries)
            queryset = queryset.filter(models.Q.create(term_queries))
            may_have_duplicates |= any(
                lookup_spawns_duplicates(self.opts, search_spec)
                for search_spec in orm_lookups
            )
        return queryset, may_have_duplicates

    def get_preserved_filters(self, request):
        """
        Return the preserved filters querystring.
        """
        match = request.resolver_match
        if self.preserve_filters and match:
            current_url = "%s:%s" % (match.app_name, match.url_name)
            changelist_url = "api_admin:%s_%s_changelist" % (
                self.opts.app_label,
                self.opts.model_name,
            )
            if current_url == changelist_url:
                preserved_filters = request.GET.urlencode()
            else:
                preserved_filters = request.GET.get("_changelist_filters")

            if preserved_filters:
                return urlencode({"_changelist_filters": preserved_filters})
        return ""

    def log_addition(self, request, obj, message):
        """
        Log that an object has been successfully added.
        The default implementation creates an admin LogEntry object.
        """
        from django_api_admin.models import ADDITION, LogEntry

        return LogEntry.objects.log_action(
            user_id=request.user.pk,
            content_type_id=get_content_type_for_model(obj).pk,
            object_id=obj.pk,
            object_repr=str(obj),
            action_flag=ADDITION,
            change_message=message,
        )

    def log_change(self, request, obj, message):
        """
        Log that an object has been successfully changed.

        The default implementation creates an admin LogEntry object.
        """
        from django_api_admin.models import CHANGE, LogEntry

        return LogEntry.objects.log_action(
            user_id=request.user.pk,
            content_type_id=get_content_type_for_model(obj).pk,
            object_id=obj.pk,
            object_repr=str(obj),
            action_flag=CHANGE,
            change_message=message,
        )

    def log_deletion(self, request, obj, object_repr):
        """
        Log that an object will be deleted. Note that this method must be
        called before the deletion.

        The default implementation creates an admin LogEntry object.
        """
        from django_api_admin.models import DELETION, LogEntry

        return LogEntry.objects.log_action(
            user_id=request.user.pk,
            content_type_id=get_content_type_for_model(obj).pk,
            object_id=obj.pk,
            object_repr=object_repr,
            action_flag=DELETION,
        )
