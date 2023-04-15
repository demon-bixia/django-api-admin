from django.contrib.admin import action
from django.contrib.admin.utils import model_ngettext
from django.utils.translation import gettext_lazy, gettext as _

from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response


@action(
    permissions=['delete'],
    description=gettext_lazy('Delete selected %(verbose_name_plural)s')
)
def delete_selected(modeladmin, request, queryset):
    """
    default api_admin action deletes the selected objects
    no confirmation page
    """
    deletable_objects, model_count, perms_needed, protected = modeladmin.get_deleted_objects(
        queryset, request)

    # check the permissions
    if perms_needed:
        objects_name = model_ngettext(queryset)
        msg = _("Cannot delete %(name)s") % {"name": objects_name}
        raise PermissionDenied(detail=msg)

    # log the deletion of all the objects inside the queryset
    n = queryset.count()
    if n:
        for obj in queryset:
            modeladmin.log_deletion(request, obj, str(obj))

    # delete the queryset
    modeladmin.delete_queryset(request, queryset)
    msg = _("Successfully deleted %(count)d %(items)s.") % {
        "count": n, "items": model_ngettext(modeladmin.opts, n)}
    return Response({'detail': msg}, status=status.HTTP_200_OK)


@action(description='make all authors old')
def make_old(model_admin, request, queryset):
    queryset.update(age=60)
    return Response({'detail': 'All select authors are old now'}, status=status.HTTP_200_OK)


@action(description='make all authors young')
def make_young(model_admin, request, queryset):
    queryset.update(age=1)
    return Response({'detail': 'All select authors are young now'}, status=status.HTTP_200_OK)
