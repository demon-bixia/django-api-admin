from django.contrib.admin import ModelAdmin
from django.contrib.admin.utils import flatten_fieldsets
from django.db import transaction, router
from django.db.models import Model
from rest_framework import serializers

from django_api_admin.serializers import ActionSerializer
from . import views as api_views


class APIModelAdmin(ModelAdmin):
    """
    everything that is ui specific is handled by the ui
    filtering is also handled by the ui
    """
    action_serializer = ActionSerializer

    # these attributes will be part of admin context json object
    admin_class_options = (
        # base model admin attributes
        'autocomplete_fields', 'raw_id_fields', 'fields', 'exclude', 'fieldsets', 'filter_vertical',
        'filter_horizontal', 'radio_fields', 'prepopulated_fields', 'readonly_fields',
        'ordering', 'sortable_by', 'view_on_site', 'show_full_result_count',
        # model admin attributes
        'list_display', 'list_display_links', 'list_filter', 'list_select_related', 'list_per_page',
        'list_max_show_all', 'list_editable', 'search_fields', 'date_hierarchy', 'save_as', 'save_on_top',
        'save_as_continue', 'preserve_filters',
    )

    # these attributes will be sent with every field
    # to the client when requesting a form.
    serializer_field_attributes = [
        'required', 'default', 'read_only', 'write_only',
        'style', 'label', 'help_text', 'allow_blank', 'allow_null',
        'initial',
        'min_length', 'max_length', 'regex',
        'max_value', 'min_value', 'max_digits', 'decimal_places',
        'choices',
        'format', 'input_formats',
    ]

    def get_admin_options(self, request):
        options_dict = {attr_name: getattr(self, attr_name, None) for attr_name in self.admin_class_options}
        return options_dict

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

    def get_serializer_class(self, request, obj=None):
        """
        Return a serializer class to be used in the model admin views
        """
        # get all fields in fieldsets
        fieldsets_fields = flatten_fieldsets(self.get_fieldsets(request, obj))
        fieldsets_fields.append('pk')
        # get excluded fields
        excluded = self.get_exclude(request, obj)
        exclude = list(excluded) if excluded is not None else None
        # get read only fields
        readonly_fields = self.get_readonly_fields(request, obj)
        # subtract excluded fields from fieldsets_fields
        fields = [field for field in fieldsets_fields if field not in exclude]

        # dynamically construct a model serializer
        return type('%sSerializer' % self.model.__name__, (serializers.ModelSerializer,), {
            'Meta': type('Meta', (object,), {
                'model': self.model,
                'fields': fields,
                'read_only_fields': readonly_fields,
            }),
        })

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

    def get_form_fields(self, serializer, change=False):
        form_fields = []

        # loop all serializer fields
        for name, field in serializer.fields.items():
            # create a field dict with name of the field and it's type
            # (i.e 'name': 'username', 'type': 'CharField', 'attrs': {'max_length': 50, ...})
            form_field = {'name': name, 'type': type(field).__name__, 'attrs': {}}

            for attr_name in self.serializer_field_attributes:
                attr = getattr(field, attr_name, None)
                # if the attribute is an empty field use null
                if attr_name == 'default' and attr.__name__ == 'empty':
                    value = None
                # if the attribute is a callable then call it and pass field to it
                elif callable(attr):
                    value = attr(field)
                else:
                    # if it's a primitive value just use it
                    value = attr
                form_field['attrs'][attr_name] = value

            if change:
                current_value = getattr(serializer.instance, name)
                if isinstance(current_value, Model):
                    current_value = current_value.pk
                form_field['attrs']['current_value'] = current_value

            form_fields.append(form_field)

        return form_fields

    def get_urls(self):
        from django.urls import path
        info = self.model._meta.app_label, self.model._meta.model_name
        admin_view = self.admin_site.api_admin_view

        return [
            path('list/', admin_view(self.list_view), name='%s_%s_list' % info),
            path('changelist/', admin_view(self.changelist_view), name='%s_%s_changelist' % info),
            path('context/', admin_view(self.admin_context_view), name='%s_%s_context' % info),
            path('perform_action/', admin_view(self.handle_action_view), name='%s_%s_perform_action' % info),
            path('add/', admin_view(self.add_view), name='%s_%s_add' % info),

            path('<path:object_id>/detail/', admin_view(self.detail_view), name='%s_%s_detail' % info),
            path('<path:object_id>/delete/', admin_view(self.delete_view), name='%s_%s_delete' % info),
            path('<path:object_id>/history/', admin_view(self.history_view), name='%s_%s_history' % info),
            path('<path:object_id>/change/', admin_view(self.change_view), name='%s_%s_change' % info),
        ]

    def admin_context_view(self, request):
        defaults = {
            'permission_classes': self.admin_site.default_permission_classes
        }
        return api_views.AdminContextView.as_view(**defaults)(request, self)

    def changelist_view(self, request, **kwargs):
        defaults = {
            'permission_classes': self.admin_site.default_permission_classes
        }
        return api_views.ChangeListView.as_view(**defaults)(request, self)

    def list_view(self, request):
        defaults = {
            'serializer_class': self.get_serializer_class(request),
            'permission_classes': self.admin_site.default_permission_classes,
        }
        return api_views.ListView.as_view(**defaults)(request, self)

    def detail_view(self, request, object_id):
        defaults = {
            'serializer_class': self.get_serializer_class(request),
            'permission_classes': self.admin_site.default_permission_classes,
        }
        return api_views.DetailView.as_view(**defaults)(request, object_id, self)

    def add_view(self, request, **kwargs):
        defaults = {
            'serializer_class': self.get_serializer_class(request),
            'permission_classes': self.admin_site.default_permission_classes,
        }
        with transaction.atomic(using=router.db_for_write(self.model)):
            return api_views.AddView.as_view(**defaults)(request, self, **kwargs)

    def change_view(self, request, object_id, **kwargs):
        defaults = {
            'serializer_class': self.get_serializer_class(request),
            'permission_classes': self.admin_site.default_permission_classes,
        }
        with transaction.atomic(using=router.db_for_write(self.model)):
            return api_views.ChangeView.as_view(**defaults)(request, object_id, self, **kwargs)

    def delete_view(self, request, object_id, extra_context=None):
        defaults = {
            'permission_classes': self.admin_site.default_permission_classes
        }
        with transaction.atomic(using=router.db_for_write(self.model)):
            return api_views.DeleteView.as_view(**defaults)(request, object_id, self)

    def handle_action_view(self, request):
        defaults = {
            'permission_classes': self.admin_site.default_permission_classes,
            'serializer_class': self.get_action_serializer(request)
        }
        return api_views.HandleActionView.as_view(**defaults)(request, self)

    def history_view(self, request, object_id, extra_context=None):
        defaults = {
            'permission_classes': self.admin_site.default_permission_classes,
            'serializer_class': self.admin_site.log_entry_serializer,
        }
        return api_views.HistoryView.as_view(**defaults)(request, object_id, self)
