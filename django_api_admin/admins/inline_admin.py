from django.contrib.admin.options import InlineModelAdmin
from django.core.exceptions import ValidationError

from django_api_admin.admins.base_admin import BaseAPIModelAdmin


class InlineAPIModelAdmin(BaseAPIModelAdmin, InlineModelAdmin):
    """
    Edit models connected with a relationship in one page
    """
    admin_style = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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

        return [
            path('list/', self.get_list_view(),
                 name='%s_%s_%s_%s_list' % info),
            path('add/', self.get_add_view(),
                 name='%s_%s_%s_%s_add' % info),
            path('<path:object_id>/detail/', self.get_detail_view(),
                 name='%s_%s_%s_%s_detail' % info),
            path('<path:object_id>/change/', self.get_change_view(),
                 name='%s_%s_%s_%s_change' % info),
            path('<path:object_id>/delete/', self.get_delete_view(),
                 name='%s_%s_%s_%s_delete' % info),
        ]

    @property
    def urls(self):
        return self.get_urls()


class TabularInlineAPI(InlineAPIModelAdmin):
    admin_style = 'tabular'


class StackedInlineAPI(InlineAPIModelAdmin):
    admin_style = 'stacked'
