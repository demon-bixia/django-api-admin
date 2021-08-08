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
    # todo add logging
    deletable_objects, model_count, perms_needed, protected = modeladmin.get_deleted_objects(queryset, request)

    if perms_needed:
        objects_name = model_ngettext(queryset)
        msg = _("Cannot delete %(name)s") % {"name": objects_name}
        raise PermissionDenied(detail=msg)

    n = queryset.count()
    modeladmin.delete_queryset(request, queryset)
    msg = _("Successfully deleted %(count)d %(items)s.") % {
        "count": n, "items": model_ngettext(modeladmin.opts, n)}
    return Response(msg, status=status.HTTP_200_OK)
