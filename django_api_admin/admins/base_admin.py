import copy

from django.contrib.auth import get_permission_codename
from django.utils.translation import gettext as _

from rest_framework.serializers import ModelSerializer

from django_api_admin.checks import APIBaseModelAdminChecks


class BaseAPIModelAdmin:
    """
    Shared behavior between APIModelAdmin, APIInlineModelAdmin.
    """
    # these are the options used in the change/add forms
    # of the model_admin
    form_options = [
        'fieldsets', 'fields',
        'save_on_top', 'save_as', 'save_as_continue',
        'view_on_site', 'radio_fields', 'prepopulated_fields',
        'filter_horizontal', 'filter_vertical', 'raw_id_fields',
        'autocomplete_fields'
    ]
    autocomplete_fields = ()
    raw_id_fields = ()
    fields = None
    exclude = None
    fieldsets = None
    base_serializer_class = ModelSerializer
    serializer_class = None
    filter_vertical = ()
    filter_horizontal = ()
    radio_fields = {}
    prepopulated_fields = {}
    serializerfield_overrides = {}
    readonly_fields = ()
    ordering = None
    sortable_by = None
    view_on_site = True
    show_full_result_count = True
    checks_class = APIBaseModelAdminChecks

    def check(self, **kwargs):
        return self.checks_class().check(self, **kwargs)

    def get_serializer_class(self):
        """
        Return a serializer class to be used in the model admin views
        """
        # check if a serializer class has already been created
        if self.serializer_class:
            return self.serializer_class

        attrs = dict()

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

        attrs["Meta"] = Meta

        # if the serializer method
        if isinstance(self.base_serializer_class, ModelSerializer):
            # merge serializerfield_overrides with the ModelSerializer.serializer_field_mapping
            overrides = copy.deepcopy(ModelSerializer.serializer_field_mapping)
            for key, value in self.serializerfield_overrides.items():
                overrides[key] = (value)
            self.serializerfield_overrides = overrides
            attrs['serializer_field_mapping'] = self.serializerfield_overrides

        # dynamically construct a model serializer
        self.serializer_class = type(data['parent_class'])(
            f'{self.model.__name__}AdminSerializer',
            (data['parent_class'],),
            attrs
        )
        return self.serializer_class

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
        if not exclude and hasattr(self.base_serializer_class, 'Meta') and hasattr(self.base_serializer_class.Meta, 'exclude'):
            exclude.extend(self.base_serializer_class.Meta.exclude)

        # Remove declared serializer fields which are in readonly_fields.
        new_attrs = dict.fromkeys(
            f for f in self.readonly_fields if f in self.base_serializer_class._declared_fields
        )
        serializer_class = type(
            self.base_serializer_class.__name__, (self.base_serializer_class,), new_attrs)

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

    def serializerfield_for_dbfield(self, db_field, **kwargs):
        """
        Hook for specifying the form Field instance for a given database Field
        instance.

        If kwargs are given, they're passed to the form Field's constructor.
        """

        # If we've got overrides for the serializerfield defined, use 'em. **kwargs
        # passed to serializerfield_for_dbfield override the defaults.
        for klass in db_field.__class__.mro():
            if klass in self.serializerfield_overrides:
                kwargs = {
                    **copy.deepcopy(self.serializerfield_overrides[klass]), **kwargs
                }
                return db_field.formfield(**kwargs)

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

    def get_queryset(self, request=None):
        """
        Return a QuerySet of all model instances that can be edited by the
        admin site. This is used by get_changelist_view.
        """
        qs = self.model._default_manager.get_queryset()
        ordering = self.ordering or ()
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
        from django_api_admin.admins.inline_admin import InlineAPIModelAdmin
        return isinstance(self, InlineAPIModelAdmin)

    def get_list_view(self):
        from django_api_admin.admin_views.model_admin_views.list import ListView

        defaults = {
            'serializer_class': self.get_serializer_class(),
            'permission_classes': self.admin_site.default_permission_classes,
            'authentication_classes': self.admin_site.authentication_classes,
            'model_admin': self,
        }
        return ListView.as_view(**defaults)

    def get_detail_view(self):
        from django_api_admin.admin_views.model_admin_views.detail import DetailView

        defaults = {
            'serializer_class': self.get_serializer_class(),
            'permission_classes': self.admin_site.default_permission_classes,
            'authentication_classes': self.admin_site.authentication_classes,
            'model_admin': self
        }
        return DetailView.as_view(**defaults)

    def get_add_view(self):
        from django_api_admin.admin_views.model_admin_views.add import AddView

        defaults = {
            'serializer_class': self.get_serializer_class(),
            'permission_classes': self.admin_site.default_permission_classes,
            'authentication_classes': self.admin_site.authentication_classes,
            'model_admin': self,
        }
        return AddView.as_view(**defaults)

    def get_change_view(self):
        from django_api_admin.admin_views.model_admin_views.change import ChangeView

        defaults = {
            'serializer_class': self.get_serializer_class(),
            'permission_classes': self.admin_site.default_permission_classes,
            'authentication_classes': self.admin_site.authentication_classes,
            'model_admin': self,
        }
        return ChangeView.as_view(**defaults)

    def get_delete_view(self):
        from django_api_admin.admin_views.model_admin_views.delete import DeleteView

        defaults = {
            'permission_classes': self.admin_site.default_permission_classes,
            'authentication_classes': self.admin_site.authentication_classes,
            'model_admin': self
        }
        return DeleteView.as_view(**defaults)

    def serializer_defines_fields(self):
        return hasattr(self.base_serializer_class, "_meta") and (
            self.base_serializer_class._meta.fields is not None or self.base_serializer_class._meta.exclude is not None
        )
