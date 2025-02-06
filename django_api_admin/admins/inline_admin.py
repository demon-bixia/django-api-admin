from django.core.exceptions import ValidationError
from django.utils.text import format_lazy

from django_api_admin.admins.base_admin import BaseAPIModelAdmin
from django_api_admin.checks import InlineAPIModelAdminChecks


class InlineAPIModelAdmin(BaseAPIModelAdmin):
    """
    Edit models connected with a relationship in one page
    """
    model = None
    fk_name = None
    extra = 3
    min_num = None
    max_num = None
    verbose_name = None
    verbose_name_plural = None
    can_delete = True
    show_change_link = False
    admin_style = None
    checks_class = InlineAPIModelAdminChecks

    def __init__(self, parent_model, admin_site,):
        self.admin_site = admin_site
        self.parent_model = parent_model
        self.opts = self.model._meta
        self.has_registered_model = admin_site.is_registered(self.model)
        super().__init__()
        if self.verbose_name_plural is None:
            if self.verbose_name is None:
                self.verbose_name_plural = self.opts.verbose_name_plural
            else:
                self.verbose_name_plural = format_lazy(
                    "{}s", self.verbose_name)
        if self.verbose_name is None:
            self.verbose_name = self.opts.verbose_name

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

    def get_urls(self):
        from django.urls import path

        info = (self.parent_model._meta.app_label, self.parent_model._meta.model_name,
                self.opts.app_label, self.opts.model_name)
        prefix = f'{self.model._meta.app_label}/{self.model._meta.model_name}'

        return [
            path(f'{prefix}/list/', self.get_list_view(),
                 name='%s_%s_%s_%s_list' % info),
            path(f'{prefix}/add/', self.get_add_view(),
                 name='%s_%s_%s_%s_add' % info),
            path(f'{prefix}/<path:object_id>/detail/', self.get_detail_view(),
                 name='%s_%s_%s_%s_detail' % info),
            path(f'{prefix}/<path:object_id>/change/', self.get_change_view(),
                 name='%s_%s_%s_%s_change' % info),
            path(f'{prefix}/<path:object_id>/delete/', self.get_delete_view(),
                 name='%s_%s_%s_%s_delete' % info),
        ]

    @property
    def urls(self):
        return self.get_urls()


class TabularInlineAPI(InlineAPIModelAdmin):
    admin_style = 'tabular'


class StackedInlineAPI(InlineAPIModelAdmin):
    admin_style = 'stacked'
