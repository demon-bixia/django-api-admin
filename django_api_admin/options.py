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
    """
    action_serializer = ActionSerializer

    def get_serializer_class(self, request, obj=None):
        """
        Return a serializer class to be used in the model admin views
        """
        # get all fields
        fields = flatten_fieldsets(self.get_fieldsets(request, obj))
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
            path('<path:object_id>/delete/', admin_view(self.delete_view), name='%s_%s_delete' % info),
            path('perform_action/', admin_view(self.handle_action_view),
                 name='%s_%s_perform_action' % info),
        ]

    def changelist_view(self, request, extra_context=None):
        defaults = {
            'permission_classes': self.admin_site.default_permission_classes
        }
        return api_views.ChangeListView.as_view(**defaults)(request, self)

    def handle_action_view(self, request, extra_context=None):
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
