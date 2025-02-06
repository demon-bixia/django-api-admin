from django.db import router, transaction
from django.utils.translation import gettext_lazy as _

from rest_framework import status
from rest_framework.response import Response
from rest_framework.exceptions import PermissionDenied, NotFound, ParseError
from rest_framework.views import APIView

from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiExample

from django_api_admin.utils.quote import unquote
from django_api_admin.utils.diff_helper import ModelDiffHelper
from django_api_admin.utils.get_form_fields import get_form_fields
from django_api_admin.utils.get_form_config import get_form_config
from django_api_admin.utils.validate_bulk_edits import validate_bulk_edits
from django_api_admin.utils.get_inlines import get_inlines
from django_api_admin.constants.vars import TO_FIELD_VAR
from django_api_admin.openapi import CommonAPIResponses, APIResponseExamples, BulkUpdates
from django_api_admin.serializers import FormFieldsSerializer, BulkUpdatesResponseSerializer


class ChangeView(APIView):
    """
    Change an existing instance of this model. if the models has inline models associated with it you 
    create, update and delete instances of the models associated with it.
    """
    serializer_class = None
    permission_classes = []
    model_admin = None

    @extend_schema(
        responses={
            200: OpenApiResponse(
                description=_(
                    "Successfully returned the field attributes list"),
                response=FormFieldsSerializer,
                examples=[
                    APIResponseExamples.field_attributes()
                ]
            ),
            403: CommonAPIResponses.permission_denied(),
            401: CommonAPIResponses.unauthorized()
        },
    )
    def get(self, request, object_id):
        obj = self.get_object(request, object_id)
        # initiate the serializer based on the request method
        serializer = self.get_serializer_instance(request, obj)
        data = dict()
        data['fields'] = get_form_fields(serializer, change=True)
        data['config'] = get_form_config(self.model_admin)
        inlines = get_inlines(request, self.model_admin, obj=obj)
        if inlines:
            data['inlines'] = inlines
        return Response(data, status=status.HTTP_200_OK)

    def update(self, request, object_id):
        with transaction.atomic(using=router.db_for_write(self.model_admin.model)):
            obj = self.get_object(request, object_id)
            opts = self.model_admin.model._meta
            helper = ModelDiffHelper(obj)

            # test user change permission in this model.
            if not self.model_admin.has_change_permission(request):
                raise PermissionDenied

            # initiate the serializer based on the request method
            serializer = self.get_serializer_instance(request, obj)

            # update and log the changes to the object
            if serializer.is_valid():
                updated_object = serializer.save()
                # response message
                msg = _(
                    f'The {opts.verbose_name} “{str(updated_object)}” was changed successfully.')
                # log the change of  change
                self.model_admin.log_change(request, updated_object, [{'changed': {
                    'name': str(updated_object._meta.verbose_name),
                    'object': str(updated_object),
                    'fields': helper.set_changed_model(updated_object).changed_fields
                }}])

                # process bulk additions
                created_inlines = []
                if request.data.get("create_inlines", None):
                    valid_serializers = validate_bulk_edits(
                        request, self.model_admin, obj, operation="create_inlines")
                    # save the inline data in a transaction.
                    for inline_serializer in valid_serializers:
                        inline_serializer.save()
                    # return the data to the user.
                    created_inlines = [
                        inline_serializer.data for inline_serializer in valid_serializers]

                # process bulk updates
                updated_inlines = []
                if request.data.get("update_inlines", None):
                    valid_serializers = validate_bulk_edits(
                        request, self.model_admin, obj, operation="update_inlines")
                    # save the inline data in a transaction.
                    for inline_serializer in valid_serializers:
                        inline_serializer.save()
                    # return the data to the user.
                    updated_inlines = [
                        inline_serializer.data for inline_serializer in valid_serializers]

                # process bulk deletes
                deleted_inlines = []
                if request.data.get("delete_inlines", None):
                    instances, deleted_inlines = validate_bulk_edits(
                        request, self.model_admin, obj, operation="delete_inlines")
                    # delete all of them
                    instances.delete()

                # return the appropriate response based on the request data
                data = {'data': serializer.data, 'detail': msg}
                if len(created_inlines):
                    data['created_inlines'] = created_inlines
                if len(updated_inlines):
                    data['updated_inlines'] = updated_inlines
                if len(deleted_inlines):
                    data['deleted_inlines'] = deleted_inlines

                return Response(data, status=status.HTTP_200_OK)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @extend_schema(
        responses={
            200: OpenApiResponse(
                description=_(
                    "Successfully returned the field attributes list"),
                response=BulkUpdatesResponseSerializer,
                examples=[
                    OpenApiExample(
                        name=_("Update Success Response"),
                        summary=_(
                            "Example of a successful Update operation response"),
                        value=BulkUpdates,
                        status_codes=["200"]
                    )
                ]
            ),
            403: CommonAPIResponses.permission_denied(),
            401: CommonAPIResponses.unauthorized()
        },
    )
    def put(self, request, object_id):
        return self.update(request, object_id)

    @extend_schema(
        responses={
            200: OpenApiResponse(
                description=_(
                    "Successfully returned the field attributes list"),
                response=BulkUpdatesResponseSerializer,
                examples=[
                    OpenApiExample(
                        name=_("Update Success Response"),
                        summary=_(
                            "Example of a successful Update operation response"),
                        value=BulkUpdates,
                        status_codes=["200"]
                    )
                ]
            ),
            403: CommonAPIResponses.permission_denied(),
            401: CommonAPIResponses.unauthorized()
        },
    )
    def patch(self, request, object_id):
        return self.update(request, object_id)

    def get_serializer_instance(self, request, obj):
        serializer = None

        if request.method == 'PATCH':
            serializer = self.serializer_class(
                instance=obj, data=request.data.get('data', {}), partial=True)

        elif request.method == 'PUT':
            serializer = self.serializer_class(
                instance=obj, data=request.data.get('data', {}))

        elif request.method == 'GET':
            serializer = self.serializer_class(instance=obj)

        return serializer

    def get_object(self, request, object_id):
        # validate the reverse to field reference
        to_field = request.query_params.get(TO_FIELD_VAR)
        if to_field and not self.model_admin.to_field_allowed(to_field):
            raise ParseError(
                {'detail': _('The field %s cannot be referenced.') % to_field})

        obj = self.model_admin.get_object(
            request, unquote(object_id), to_field)

        # if the object doesn't exist respond with not found
        if obj is None:
            msg = _("%(name)s with ID “%(key)s” doesn't exist. Perhaps it was deleted?") % {
                'name': self.model_admin.model._meta.verbose_name,
                'key': unquote(object_id),
            }
            raise NotFound({'detail': msg})

        return obj
