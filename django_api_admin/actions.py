from django.utils.translation import gettext_lazy, gettext as _

from rest_framework import status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from django_api_admin.utils.model_ngettext import model_ngettext
from django_api_admin.utils.get_deleted_objects import get_deleted_objects
from django_api_admin.decorators import action


@action(
    permissions=['delete'],
    description=gettext_lazy('Delete selected %(verbose_name_plural)s')
)
def delete_selected(modeladmin, request, queryset):
    """
    default api_admin action deletes the selected objects
    no confirmation page
    """
    _deletable_objects, _model_count, perms_needed, _protected = get_deleted_objects(
        queryset, request, modeladmin.admin_site)

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
    queryset.delete()
    msg = _("Successfully deleted %s %s.") % (
        n, model_ngettext(modeladmin.opts, n))
    return Response({'detail': msg}, status=status.HTTP_200_OK)
