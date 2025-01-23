from django.contrib.admin.options import ModelAdmin
from django.db import models
from django.core.exceptions import FieldDoesNotExist
from django.utils.safestring import mark_safe
from django.utils.text import capfirst, smart_split, unescape_string_literal
from django.urls import include, path

from rest_framework import serializers

from django_api_admin.admins.base_admin import BaseAPIModelAdmin
from django_api_admin.serializers import ActionSerializer
from django_api_admin.views.admin_views.changelist import ChangeListView
from django_api_admin.views.admin_views.handle_action import HandleActionView
from django_api_admin.views.admin_views.history import HistoryView
from django_api_admin.utils.model_format_dict import model_format_dict
from django_api_admin.utils.lookup_spawns_duplicates import lookup_spawns_duplicates
from django_api_admin.changelist import ChangeList


class APIModelAdmin(BaseAPIModelAdmin, ModelAdmin):
    """
    exposes django.contrib.admin.options.ModelAdmin as a restful api.
    everything that is ui specific is handled by the ui
    filtering is also handled by the ui
    """
    action_serializer = ActionSerializer

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

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
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
        return type('%sActionSerializer' % self.__class__.__name__, (ActionSerializer,), {
            'action': serializers.ChoiceField(choices=[*self.get_action_choices(request)]),
            'selected_ids': serializers.MultipleChoiceField(choices=[*self.get_selected_ids()])
        })

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

    def get_changelist_instance(self, request):
        """
        Return a `ChangeList` instance based on `request`. May raise
        `IncorrectLookupParameters`.
        """
        list_display = self.list_display
        list_display_links = self.get_list_display_links(list_display)
        # Add the action checkboxes if any actions are available.
        if self.get_actions(request):
            list_display = ["action_checkbox", *list_display]
        sortable_by = self.get_sortable_by(request)
        return ChangeList(
            request,
            self.model,
            list_display,
            list_display_links,
            self.get_list_filter(request),
            self.date_hierarchy,
            self.get_search_fields(request),
            self.get_list_select_related(request),
            self.list_per_page,
            self.list_max_show_all,
            self.list_editable,
            self,
            sortable_by,
            self.search_help_text
        )

    def get_empty_value_display(self):
        """
        Return the empty_value_display set on ModelAdmin or AdminSite.
        """
        try:
            return mark_safe(self.empty_value_display)
        except AttributeError:
            return mark_safe(self.admin_site.empty_value_display)

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

    def get_urls(self):
        info = self.model._meta.app_label, self.model._meta.model_name

        urlpatterns = [
            path('list/', self.get_list_view(), name='%s_%s_list' % info),
            path('changelist/', self.get_changelist_view(),
                 name='%s_%s_changelist' % info),
            path('perform_action/', self.get_handle_action_view(),
                 name='%s_%s_perform_action' % info),
            path('add/', self.get_add_view(), name='%s_%s_add' % info),
            path('<path:object_id>/detail/', self.get_detail_view(),
                 name='%s_%s_detail' % info),
            path('<path:object_id>/delete/', self.get_delete_view(),
                 name='%s_%s_delete' % info),
            path('<path:object_id>/history/',
                 self.get_history_view(), name='%s_%s_history' % info),
            path('<path:object_id>/change/', self.get_change_view(),
                 name='%s_%s_change' % info),
        ]

        # add Inline admins urls
        for inline_class in self.inlines:
            inline = inline_class(self.model, self.admin_site)
            opts = inline.model._meta
            urlpatterns.insert(0, *[
                path('%s/%s/' % (opts.app_label, opts.model_name),
                     include(inline.urls)),
            ])
        return urlpatterns

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

    def get_changelist_view(self):
        defaults = {
            'permission_classes': self.admin_site.default_permission_classes,
            'model_admin': self
        }
        return ChangeListView.as_view(**defaults)

    def get_handle_action_view(self):
        defaults = {
            'permission_classes': self.admin_site.default_permission_classes,
            'model_admin': self
        }
        return HandleActionView.as_view(**defaults)

    def get_history_view(self):
        defaults = {
            'permission_classes': self.admin_site.default_permission_classes,
            'serializer_class': self.admin_site.log_entry_serializer,
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
