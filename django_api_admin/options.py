"""
API model admin.
"""

from django.contrib.admin.options import InlineModelAdmin, ModelAdmin
from django.contrib.admin.utils import flatten_fieldsets
from django.contrib.auth import get_permission_codename
from django.db import router, transaction
from rest_framework import serializers

from django_api_admin.views import admin_views
from django_api_admin.serializers import ActionSerializer


class BaseAPIModelAdmin:
    """
    Shared behavior between APIModelAdmin, APIInlineModelAdmin.
    """
    # these are the options used in the change/add forms
    # of the model_admin
    form_options = [
        'fieldsets', 'fields',

        'save_on_top', 'save_as', 'save_as_continue',

        'view_on_site',
    ]

    def get_serializer_class(self, request, obj=None, changelist=False):
        """
        Return a serializer class to be used in the model admin views
        """
        # get all fields in fieldsets
        fieldsets_fields = flatten_fieldsets(self.get_fieldsets(request, obj))
        fieldsets_fields.append('pk')
        # get excluded fields
        excluded = self.get_exclude(request, obj)
        exclude = list(excluded) if excluded is not None else []
        # get read only fields
        readonly_fields = self.get_readonly_fields(request, obj)
        # subtract excluded fields from fieldsets_fields
        fields = [field for field in fieldsets_fields if field not in exclude]

        # if it's a changelist include all the fields because the hiding happens in the changelist view
        if changelist:
            fields = '__all__'

        # dynamically construct a model serializer
        return type('%sSerializer' % self.model.__name__, (serializers.ModelSerializer,), {
            'Meta': type('Meta', (object,), {
                'model': self.model,
                'fields': fields,
                'read_only_fields': readonly_fields,
            }),
        })

    def get_permission_map(self, request, obj=None):
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

    def has_add_permission(self, request, obj=None):
        opts = self.opts
        codename = get_permission_codename('add', opts)
        return request.user.has_perm("%s.%s" % (opts.app_label, codename))

    def has_change_permission(self, request, obj=None):
        opts = self.opts
        codename = get_permission_codename('change', opts)
        return request.user.has_perm("%s.%s" % (opts.app_label, codename))

    def has_delete_permission(self, request, obj=None):
        opts = self.opts
        codename = get_permission_codename('delete', opts)
        return request.user.has_perm("%s.%s" % (opts.app_label, codename))

    def has_view_permission(self, request, obj=None):
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
            'serializer_class': self.get_serializer_class(request),
            'permission_classes': self.admin_site.default_permission_classes,
        }
        return admin_views.ListView.as_view(**defaults)(request, self)

    def detail_view(self, request, object_id):
        defaults = {
            'serializer_class': self.get_serializer_class(request),
            'permission_classes': self.admin_site.default_permission_classes,
        }
        return admin_views.DetailView.as_view(**defaults)(request, object_id, self)

    def add_view(self, request, **kwargs):
        defaults = {
            'serializer_class': self.get_serializer_class(request),
            'permission_classes': self.admin_site.default_permission_classes,
        }
        with transaction.atomic(using=router.db_for_write(self.model)):
            return admin_views.AddView.as_view(**defaults)(request, self, **kwargs)

    def change_view(self, request, object_id, **kwargs):
        defaults = {
            'serializer_class': self.get_serializer_class(request),
            'permission_classes': self.admin_site.default_permission_classes,
        }
        with transaction.atomic(using=router.db_for_write(self.model)):
            return admin_views.ChangeView.as_view(**defaults)(request, object_id, self, **kwargs)

    def delete_view(self, request, object_id, **kwargs):
        defaults = {
            'permission_classes': self.admin_site.default_permission_classes
        }
        with transaction.atomic(using=router.db_for_write(self.model)):
            return admin_views.DeleteView.as_view(**defaults)(request, object_id, self, **kwargs)


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
        return admin_views.ChangeListView.as_view(**defaults)(request, self)

    def handle_action_view(self, request):
        defaults = {
            'permission_classes': self.admin_site.default_permission_classes,
            'serializer_class': self.get_action_serializer(request)
        }
        return admin_views.HandleActionView.as_view(**defaults)(request, self)

    def history_view(self, request, object_id, extra_context=None):
        defaults = {
            'permission_classes': self.admin_site.default_permission_classes,
            'serializer_class': self.admin_site.log_entry_serializer,
        }
        return admin_views.HistoryView.as_view(**defaults)(request, object_id, self)


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
