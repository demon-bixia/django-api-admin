from django.db import router, transaction
from django.utils.translation import gettext_lazy as _

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied

from django_api_admin.utils.quote import unquote
from django_api_admin.constants.vars import TO_FIELD_VAR


class DeleteView(APIView):
    """
    Delete a single object from this model
    """
    permission_classes = []
    model_admin = None

    def delete(self, request, object_id):
        with transaction.atomic(using=router.db_for_write(self.model_admin.model)):
            opts = self.model_admin.model._meta

            # validate the reverse to field reference.
            to_field = request.query_params.get(TO_FIELD_VAR)
            if to_field and not self.model_admin.to_field_allowed(to_field):
                return Response({'detail': _('The field %s cannot be referenced.' % to_field)},
                                status=status.HTTP_400_BAD_REQUEST)
            obj = self.model_admin.get_object(
                request, unquote(object_id), to_field)

            if obj is None:
                msg = _("%(name)s with ID “%(key)s” doesn't exist. Perhaps it was deleted?") % {
                    'name': opts.verbose_name,
                    'key': unquote(object_id),
                }
                return Response({'detail': msg}, status=status.HTTP_404_NOT_FOUND)

            # check delete object permission
            if not self.model_admin.has_delete_permission(request):
                raise PermissionDenied

            # log deletion
            self.model_admin.log_deletion(request, obj, str(obj))

            # delete the object
            obj.delete()

            return Response({'detail': _('The %(name)s “%(obj)s” was deleted successfully.') % {
                'name': opts.verbose_name,
                'obj': str(obj),
            }}, status=status.HTTP_200_OK)

    def post(self, *args, **kwargs):
        return self.delete(*args, **kwargs)
