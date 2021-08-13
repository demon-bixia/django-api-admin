from django.contrib.admin import ModelAdmin
from django.contrib.admin.utils import flatten_fieldsets
from django.db import transaction, router
from rest_framework.serializers import ModelSerializer

from django_api_admin.serializers import ActionSerializer
from . import views as api_views


class APIModelAdmin(ModelAdmin):
    """
    everything that is ui specific is handled by the ui
    filtering is also handled by the ui
    Todo make a view for the client to check all permissions of a user
    Todo model admin attributes should be returned using a separate view
    Todo there should be a list view and a changelist view
    """
    action_serializer = ActionSerializer

    def get_serializer_class(self, request, obj=None):
        """
        Return a serializer class to be used in the model admin views
        """
        # get all fields
        fields = flatten_fieldsets(self.get_fieldsets(request, obj))
        fields.append('pk')
        # add readonly to exclude
        excluded = self.get_exclude(request, obj)
        exclude = list(excluded) if excluded is not None else None
        readonly_fields = self.get_readonly_fields(request, obj)

        # dynamically construct a model serializer
        return type('%sSerializer' % self.model.__name__, (ModelSerializer,), {
            'Meta': type('Meta', (object,), {
                'model': self.model,
                'fields': fields,
                'exclude': exclude,
                'read_only_fields': readonly_fields,
            }),
        })

    def get_action_serializer(self, request):
        from rest_framework import serializers
        return type('%sActionSerializer' % self.__class__.__name__, (ActionSerializer,), {
            'action': serializers.ChoiceField(choices=[*self.get_action_choices(request)]),
        })

    def get_urls(self):
        from django.urls import path
        info = self.model._meta.app_label, self.model._meta.model_name
        admin_view = self.admin_site.api_admin_view

        return [
            path('', admin_view(self.changelist_view), name='%s_%s_changelist' % info),
            path('perform_action/', admin_view(self.handle_action_view),
                 name='%s_%s_perform_action' % info),
            path('add/', admin_view(self.add_view), name='%s_%s_add' % info),
            path('<path:object_id>/delete/', admin_view(self.delete_view), name='%s_%s_delete' % info),
            path('<path:object_id>/history/', admin_view(self.history_view), name='%s_%s_history' % info),
            path('<path:object_id>/change/', admin_view(self.change_view), name='%s_%s_change' % info),
        ]

    def changelist_view(self, request, extra_context=None):
        defaults = {
            'permission_classes': self.admin_site.default_permission_classes
        }
        return api_views.ChangeListView.as_view(**defaults)(request, self)

    def handle_action_view(self, request):
        defaults = {
            'permission_classes': self.admin_site.default_permission_classes
        }
        return api_views.HandleActionView.as_view(**defaults)(request, self)

    def delete_view(self, request, object_id, extra_context=None):
        defaults = {
            'permission_classes': self.admin_site.default_permission_classes
        }
        with transaction.atomic(using=router.db_for_write(self.model)):
            return api_views.DeleteView.as_view(**defaults)(request, object_id, self)

    def history_view(self, request, object_id, extra_context=None):
        defaults = {
            'permission_classes': self.admin_site.default_permission_classes,
            'serializer_class': self.admin_site.log_entry_serializer,
            'pagination_class': self.admin_site.default_pagination_class,
        }
        return api_views.HistoryView.as_view(**defaults)(request, object_id, self)

    def add_view(self, request, **kwargs):
        defaults = {
            'serializer_class': self.get_serializer_class(request),
            'permission_classes': self.admin_site.default_permission_classes,
        }
        with transaction.atomic(using=router.db_for_write(self.model)):
            return api_views.AddView.as_view(**defaults)(request, self)

    def change_view(self, request, object_id, **kwargs):
        defaults = {
            'serializer_class': self.get_serializer_class(request),
            'permission_classes': self.admin_site.default_permission_classes,
        }
        with transaction.atomic(using=router.db_for_write(self.model)):
            return api_views.ChangeView.as_view(**defaults)(request, object_id, self)
