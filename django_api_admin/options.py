"""
API model admin.
"""
from django.contrib.admin.options import InlineModelAdmin, ModelAdmin
from django.contrib.auth import get_permission_codename
from django.db import router, transaction
from django.core.exceptions import FieldDoesNotExist

from rest_framework import serializers

from django_api_admin.serializers import ActionSerializer
from django_api_admin.views.admin_views.add import AddView
from django_api_admin.views.admin_views.change import ChangeView
from django_api_admin.views.admin_views.changelist import ChangeListView
from django_api_admin.views.admin_views.delete import DeleteView
from django_api_admin.views.admin_views.detail import DetailView
from django_api_admin.views.admin_views.handle_action import HandleActionView
from django_api_admin.views.admin_views.history import HistoryView
from django_api_admin.views.admin_views.list import ListView


class BaseAPIModelAdmin:
    """
    Shared behavior between APIModelAdmin, APIInlineModelAdmin.
    """
    # these are the options used in the change/add forms
    # of the model_admin
    serializer_class = serializers.ModelSerializer

    form_options = [
        'fieldsets', 'fields',
        'save_on_top', 'save_as', 'save_as_continue',
        'view_on_site',
    ]

    def get_serializer_class(self):
        """
        Return a serializer class to be used in the model admin views
        """
        # get all fields in fieldsets
        fields = self.get_fields()
        fields.append('pk')

        # get the data needed to create the serializer_class for this model
        data = self.get_serializer_data()

        # subtract excluded fields from fieldsets_fields
        fields = [
            field for field in fields if field not in data['exclude']]

        # if the parent model serializer defines a meta class we need to inherit from
        # that meta class
        Meta = type("Meta", data['bases'], {
            'model': self.model,
            'fields': fields,
            'read_only_fields': self.readonly_fields,
        })

        # dynamically construct a model serializer
        return type(data['parent_class'])(
            f'{self.model.__name__}Serializer',
            (data['parent_class'],),
            {'Meta': Meta}
        )

    def get_fields(self):
        """
        Hook for specifying fields.
        """
        if self.fields:
            return self.fields
        data = self.get_serializer_data()

        # if the parent model serializer defines a meta class we need to inherit from
        # that meta class
        attrs = {'model': data['model']}
        if data['fields'] == '__all__':
            attrs['fields'] = data['fields']
        else:
            attrs['exclude'] = data['exclude']
        # create the meta class
        Meta = type("Meta", data['bases'], attrs)

        serializer_class = type(data['parent_class'])(
            data['name'], (data['parent_class'],), {'Meta': Meta})
        return [*serializer_class().fields, *self.readonly_fields]

    def get_serializer_data(self):
        # get excluded fields
        exclude = list(self.exclude) if self.exclude else []
        if not exclude and hasattr(self.serializer_class, 'Meta') and hasattr(self.serializer_class.Meta, 'exclude'):
            exclude.extend(self.serializer_class.Meta.exclude)

        # Remove declared serializer fields which are in readonly_fields.
        new_attrs = dict.fromkeys(
            f for f in self.readonly_fields if f in self.serializer_class._declared_fields
        )
        serializer_class = type(
            self.serializer_class.__name__, (self.serializer_class,), new_attrs)

        fields = self.fieldsets or self.fields

        if fields is None and not self.serializer_defines_fields():
            fields = '__all__'

        # If parent form class already has an inner Meta, the Meta we're
        # creating needs to inherit from the parent's inner meta.
        bases = (serializer_class.Meta,) if hasattr(
            serializer_class, "Meta") else ()

        # dynamically construct a model serializer
        return {
            'parent_class': serializer_class,
            'name': f'{self.model.__name__}Serializer',
            'model': self.model,
            'bases': bases,
            'fields': fields,
            'exclude': exclude,
            'read_only_fields': self.readonly_fields,
        }

    def get_permission_map(self, request):
        """
        return a dictionary of user permissions in this module.
        """

        return {
            'has_add_permission': self.has_add_permission(request),
            'has_change_permission': self.has_change_permission(request),
            'has_delete_permission': self.has_delete_permission(request),
            'has_view_permission': self.has_view_permission(request),
            'has_view_or_change_permission': self.has_view_or_change_permission(request),
            'has_module_permission': self.has_module_permission(request),
        }

    def get_queryset(self, request):
        """
        Return a QuerySet of all model instances that can be edited by the
        admin site. This is used by changelist_view.
        """
        qs = self.model._default_manager.get_queryset()
        ordering = self.get_ordering(request)
        if ordering:
            qs = qs.order_by(*ordering)
        return qs

    def has_add_permission(self, request):
        opts = self.opts
        codename = get_permission_codename('add', opts)
        return request.user.has_perm("%s.%s" % (opts.app_label, codename))

    def has_change_permission(self, request):
        opts = self.opts
        codename = get_permission_codename('change', opts)
        return request.user.has_perm("%s.%s" % (opts.app_label, codename))

    def has_delete_permission(self, request):
        opts = self.opts
        codename = get_permission_codename('delete', opts)
        return request.user.has_perm("%s.%s" % (opts.app_label, codename))

    def has_view_permission(self, request):
        opts = self.opts
        codename_view = get_permission_codename('view', opts)
        codename_change = get_permission_codename('change', opts)
        return (
            request.user.has_perm('%s.%s' % (opts.app_label, codename_view)) or
            request.user.has_perm('%s.%s' % (opts.app_label, codename_change))
        )

    def has_view_or_change_permission(self, request, obj=None):
        return self.has_view_permission(request) or self.has_change_permission(request)

    def has_module_permission(self, request):
        return request.user.has_module_perms(self.opts.app_label)

    @property
    def is_inline(self):
        return isinstance(self, InlineModelAdmin)

    def list_view(self, request):
        defaults = {
            'serializer_class': self.get_serializer_class(),
            'permission_classes': self.admin_site.default_permission_classes,
        }
        return ListView.as_view(**defaults)(request, self)

    def detail_view(self, request, object_id):
        defaults = {
            'serializer_class': self.get_serializer_class(),
            'permission_classes': self.admin_site.default_permission_classes,
        }
        return DetailView.as_view(**defaults)(request, object_id, self)

    def add_view(self, request, **kwargs):
        defaults = {
            'serializer_class': self.get_serializer_class(),
            'permission_classes': self.admin_site.default_permission_classes,
        }
        with transaction.atomic(using=router.db_for_write(self.model)):
            return AddView.as_view(**defaults)(request, self, **kwargs)

    def change_view(self, request, object_id, **kwargs):
        defaults = {
            'serializer_class': self.get_serializer_class(),
            'permission_classes': self.admin_site.default_permission_classes,
        }
        with transaction.atomic(using=router.db_for_write(self.model)):
            return ChangeView.as_view(**defaults)(request, object_id, self, **kwargs)

    def delete_view(self, request, object_id, **kwargs):
        defaults = {
            'permission_classes': self.admin_site.default_permission_classes
        }
        with transaction.atomic(using=router.db_for_write(self.model)):
            return DeleteView.as_view(**defaults)(request, object_id, self, **kwargs)

    def serializer_defines_fields(self):
        return hasattr(self.serializer_class, "_meta") and (
            self.serializer_class._meta.fields is not None or self.serializer_class._meta.exclude is not None
        )


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

    def get_action_serializer(self, request):
        return type('%sActionSerializer' % self.__class__.__name__, (ActionSerializer,), {
            'action': serializers.ChoiceField(choices=[*self.get_action_choices(request)]),
            'selected_ids': serializers.MultipleChoiceField(choices=[*self.get_selected_ids(request)])
        })

    def get_selected_ids(self, request):
        queryset = self.get_queryset(request)
        choices = []
        for item in queryset:
            choices.append((f'{item.pk}', f'{str(item)}'))
        return choices

    def get_urls(self):
        from django.urls import include, path

        info = self.model._meta.app_label, self.model._meta.model_name
        admin_view = self.admin_site.api_admin_view

        urlpatterns = [
            path('list/', admin_view(self.list_view), name='%s_%s_list' % info),
            path('changelist/', admin_view(self.changelist_view),
                 name='%s_%s_changelist' % info),
            path('perform_action/', admin_view(self.handle_action_view),
                 name='%s_%s_perform_action' % info),
            path('add/', admin_view(self.add_view), name='%s_%s_add' % info),
            path('<path:object_id>/detail/', admin_view(self.detail_view),
                 name='%s_%s_detail' % info),
            path('<path:object_id>/delete/', admin_view(self.delete_view),
                 name='%s_%s_delete' % info),
            path('<path:object_id>/history/',
                 admin_view(self.history_view), name='%s_%s_history' % info),
            path('<path:object_id>/change/', admin_view(self.change_view),
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

    def changelist_view(self, request, **kwargs):
        defaults = {
            'permission_classes': self.admin_site.default_permission_classes
        }
        return ChangeListView.as_view(**defaults)(request, self)

    def handle_action_view(self, request):
        defaults = {
            'permission_classes': self.admin_site.default_permission_classes,
            'serializer_class': self.get_action_serializer(request)
        }
        return HandleActionView.as_view(**defaults)(request, self)

    def history_view(self, request, object_id, extra_context=None):
        defaults = {
            'permission_classes': self.admin_site.default_permission_classes,
            'serializer_class': self.admin_site.log_entry_serializer,
        }
        return HistoryView.as_view(**defaults)(request, object_id, self)

    def to_field_allowed(self, request, to_field):
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


class InlineAPIModelAdmin(BaseAPIModelAdmin, InlineModelAdmin):
    """
    Edit models connected with a relationship in one page
    """
    admin_style = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_object(self, request, object_id):
        queryset = self.get_queryset(request)
        model = queryset.model
        try:
            return queryset.get(pk=object_id)
        except model.DoesNotExist:
            return None

    def get_urls(self):
        from django.urls import path

        info = (self.parent_model._meta.app_label, self.parent_model._meta.model_name,
                self.opts.app_label, self.opts.model_name)
        admin_view = self.admin_site.api_admin_view

        return [
            path('list/', admin_view(self.list_view),
                 name='%s_%s_%s_%s_list' % info),
            path('add/', admin_view(self.add_view),
                 name='%s_%s_%s_%s_add' % info),
            path('<path:object_id>/detail/', admin_view(self.detail_view),
                 name='%s_%s_%s_%s_detail' % info),
            path('<path:object_id>/change/', admin_view(self.change_view),
                 name='%s_%s_%s_%s_change' % info),
            path('<path:object_id>/delete/', admin_view(self.delete_view),
                 name='%s_%s_%s_%s_delete' % info),
        ]

    @property
    def urls(self):
        return self.get_urls()


class TabularInlineAPI(InlineAPIModelAdmin):
    admin_style = 'tabular'


class StackedInlineAPI(InlineAPIModelAdmin):
    admin_style = 'stacked'
