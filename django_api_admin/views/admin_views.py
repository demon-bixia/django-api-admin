"""
Model admin views.
"""
from django.db.models import Model
from django.db import transaction
from django.utils.translation import gettext_lazy as _
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldDoesNotExist, ObjectDoesNotExist
from django.contrib.admin.utils import label_for_field, lookup_field, unquote
from django.contrib.admin.options import (TO_FIELD_VAR,
                                          IncorrectLookupParameters,
                                          get_content_type_for_model)

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.reverse import reverse
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, PermissionDenied

from django_api_admin.declarations.classes import ModelDiffHelper
from django_api_admin.declarations.functions import (get_form_fields,
                                                     get_form_config,
                                                     validate_bulk_edits,
                                                     get_inlines)


class ListView(APIView):
    """
    Return a list containing all instances of this model.
    """

    serializer_class = None
    permission_classes = []

    def get(self, request, admin):
        queryset = admin.get_queryset(request)
        page = admin.admin_site.paginate_queryset(queryset, request, view=self)
        serializer = self.serializer_class(page, many=True)
        data = serializer.data
        info = (
            admin.admin_site.name,
            admin.model._meta.app_label,
            admin.model._meta.model_name
        )
        pattern = '%s:%s_%s_detail'

        for item in data:
            item['detail_url'] = reverse(pattern % info, kwargs={
                'object_id': int(item['pk'])}, request=request)
        return Response(data, status=status.HTTP_200_OK)


class DetailView(APIView):
    """
    GET one instance of this model using pk and to_fields.
    """
    permission_classes = []
    serializer_class = None

    def get(self, request, object_id, admin):
        # validate the reverse to field reference
        to_field = request.query_params.get(TO_FIELD_VAR)
        if to_field and not admin.to_field_allowed(request, to_field):
            return Response({'detail': 'The field %s cannot be referenced.' % to_field},
                            status=status.HTTP_400_BAD_REQUEST)
        obj = admin.get_object(request, unquote(object_id), to_field)

        # if the object doesn't exist respond with not found
        if obj is None:
            msg = _("%(name)s with ID “%(key)s” doesn't exist. Perhaps it was deleted?") % {
                'name': admin.model._meta.verbose_name,
                'key': unquote(object_id),
            }
            return Response({'detail': msg}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.serializer_class(obj)
        data = serializer.data

        # add admin urls.
        info = (
            admin.admin_site.name,
            admin.model._meta.app_label,
            admin.model._meta.model_name,
        )
        pattern = '%s:%s_%s_'
        data['history_url'] = reverse((pattern + 'history') % info, kwargs={'object_id': data['pk']},
                                      request=request)
        if admin.view_on_site:
            model_type = ContentType.objects.get_for_model(
                model=admin.model)
            data['view_on_site'] = reverse('%s:view_on_site' % admin.admin_site.name,
                                           kwargs={
                                               'content_type_id': model_type.pk, 'object_id': obj.pk},
                                           request=request)

        data['list_url'] = reverse((pattern + 'list') % info, request=request)
        data['delete_url'] = reverse(
            (pattern + 'delete') % info, kwargs={'object_id': data['pk']}, request=request)
        data['change_url'] = reverse(
            (pattern + 'change') % info, kwargs={'object_id': data['pk']}, request=request)
        return Response(data, status=status.HTTP_200_OK)


class AddView(APIView):
    """
    Add new instances of this model. if this model has inline models associated with it 
    you can also add inline instances to this model.

    a request body should look like this:

    {
        "data": {
            // the values to create new instance of the model
            "name": "lorem ipsum"
            ...
        },
        // the inline instances you want to create (optional)
        "create_inlines": {
            "books": [
                {
                    "title": "lorem ipsum"
                    ...
                },
                {
                    "title": "lorem ipsum"
                    ...
                },
            ]
        }
    }
    """
    serializer_class = None
    permission_classes = []

    def get(self, request, model_admin):
        data = dict()
        serializer = self.serializer_class()
        data['fields'] = get_form_fields(serializer)
        data['config'] = get_form_config(model_admin)
        inlines = get_inlines(request, model_admin)
        if len(inlines):
            data['inlines'] = inlines
        return Response(data, status=status.HTTP_200_OK)

    @transaction.atomic
    def post(self, request, model_admin):
        # if the user doesn't have added permission respond with permission denied
        if not model_admin.has_add_permission(request):
            raise PermissionDenied

        # validate data and send
        serializer = self.serializer_class(data=request.data.get('data', {}))
        if serializer.is_valid():
            # create the new object
            opts = model_admin.model._meta
            new_object = serializer.save()
            msg = _(
                f'The {opts.verbose_name} “{str(new_object)}” was added successfully.')

            # setup arguments used to log additions
            model_admin = model_admin
            change_object = new_object

            # log addition of the new instance
            model_admin.log_addition(request, change_object, [{'added': {
                'name': str(new_object._meta.verbose_name),
                'object': str(new_object),
            }}])

            # process bulk additions
            created_inlines = []
            if request.data.get("create_inlines", None):
                valid_serializers = validate_bulk_edits(
                    request, model_admin, new_object)
                # save the inline data in a transaction.
                for inline_serializer in valid_serializers:
                    inline_serializer.save()
                # return the data to the user.
                created_inlines = [
                    inline_serializer.data for inline_serializer in valid_serializers]

            # return the appropriate 201 response based on the data
            data = {'data': serializer.data, 'detail': msg}
            if len(created_inlines):
                data['created_inlines'] = created_inlines

            return Response(data, status=status.HTTP_201_CREATED)
        else:
            # return a 400 response indicating failure
            return Response({"errors": serializer.errors}, status=status.HTTP_400_BAD_REQUEST)


class ChangeView(APIView):
    """
    Change an existing instance of this model. if the models has inline models associated with it you 
    create, update and delete instances of the models associated with it.

        {
        "data": {
            // the values to create new instance of the model
            "name": "lorem ipsum"
            ...
        },
        // the inline instances you want to create (optional)
        "create_inlines": {
            "books": [
                {
                    "title": "lorem ipsum"
                    ...
                },
            ]
        },
        // the inline instances you want to update make sure you include a pk field (optional)
        "update_inlines": {
            "books": [
                {
                    "pk":10,
                    "title": "lorem ipsum"
                    ...
                },
            ]
        },
        // the inline instances you want to delete make sure you include a pk field (optional)
        "delete_inlines": {
            "books": [
                {
                    "pk":10
                },
            ]
        }
    }
    """
    serializer_class = None
    permission_classes = []

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

    @transaction.atomic
    def update(self, request, object_id, model_admin):
        # validate the reverse to field reference
        to_field = request.query_params.get(TO_FIELD_VAR)
        if to_field and not model_admin.to_field_allowed(request, to_field):
            return Response({'detail': 'The field %s cannot be referenced.' % to_field},
                            status=status.HTTP_400_BAD_REQUEST)
        obj = model_admin.get_object(request, unquote(object_id), to_field)
        opts = model_admin.model._meta
        helper = ModelDiffHelper(obj)

        # if the object doesn't exist respond with not found
        if obj is None:
            msg = _("%(name)s with ID “%(key)s” doesn't exist. Perhaps it was deleted?") % {
                'name': model_admin.model._meta.verbose_name,
                'key': unquote(object_id),
            }
            return Response({'detail': msg}, status=status.HTTP_404_NOT_FOUND)

        # test user change permission in this model.
        if not model_admin.has_change_permission(request, obj):
            raise PermissionDenied

        # initiate the serializer based on the request method
        serializer = self.get_serializer_instance(request, obj)

        # if the method is get return the change form fields dictionary
        if request.method == 'GET':
            data = dict()
            data['fields'] = get_form_fields(serializer, change=True)
            data['config'] = get_form_config(model_admin)
            inlines = get_inlines(request, model_admin, obj=obj)
            if inlines:
                data['inlines'] = inlines
            return Response(data, status=status.HTTP_200_OK)

        # update and log the changes to the object
        if serializer.is_valid():
            updated_object = serializer.save()
            # response message
            msg = _(
                f'The {opts.verbose_name} “{str(updated_object)}” was changed successfully.')
            # setup arguments used to log additions
            changed_object = updated_object
            # log the change of  change
            model_admin.log_change(request, changed_object, [{'changed': {
                'name': str(updated_object._meta.verbose_name),
                'object': str(updated_object),
                'fields': helper.set_changed_model(updated_object).changed_fields
            }}])

            # process bulk edits
            created_inlines = []
            if request.data.get("create_inlines", None):
                valid_serializers = validate_bulk_edits(
                    request, model_admin, obj, operation="create_inlines")
                # save the inline data in a transaction.
                for inline_serializer in valid_serializers:
                    inline_serializer.save()
                # return the data to the user.
                created_inlines = [
                    inline_serializer.data for inline_serializer in valid_serializers]

            # process bulk edits
            updated_inlines = []
            if request.data.get("update_inlines", None):
                valid_serializers = validate_bulk_edits(
                    request, model_admin, obj, operation="update_inlines")
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
                    request, model_admin, obj, operation="delete_inlines")
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

    def get(self, request, object_id, admin):
        return self.update(request, object_id, admin)

    def put(self, request, object_id, admin):
        return self.update(request, object_id, admin)

    def patch(self, request, object_id, admin):
        return self.update(request, object_id, admin)


class DeleteView(APIView):
    """
    Delete a single object from this model
    """
    permission_classes = []

    def delete(self, request, object_id, admin):
        opts = admin.model._meta

        # validate the reverse to field reference.
        to_field = request.query_params.get(TO_FIELD_VAR)
        if to_field and not admin.to_field_allowed(request, to_field):
            return Response({'detail': 'The field %s cannot be referenced.' % to_field},
                            status=status.HTTP_400_BAD_REQUEST)
        obj = admin.get_object(request, unquote(object_id), to_field)

        if obj is None:
            msg = _("%(name)s with ID “%(key)s” doesn't exist. Perhaps it was deleted?") % {
                'name': opts.verbose_name,
                'key': unquote(object_id),
            }
            return Response({'detail': msg}, status=status.HTTP_404_NOT_FOUND)

        # check delete object permission
        if not admin.has_delete_permission(request, obj):
            raise PermissionDenied

        model_admin = admin

        # log deletion
        model_admin.log_deletion(request, obj, str(obj))

        # delete the object
        obj.delete()

        return Response({'detail': _('The %(name)s “%(obj)s” was deleted successfully.') % {
            'name': opts.verbose_name,
            'obj': str(obj),
        }}, status=status.HTTP_200_OK)

    def post(self, *args, **kwargs):
        return self.delete(*args, **kwargs)


class ChangeListView(APIView):
    """
    Return a JSON object representing the django admin changelist table.
    supports querystring filtering, pagination and search also changes based on list display.
    Note: this is different from the list all objects view.
    example of returned JSON object:

    {
        config: {
            "list_display": ["name", "age"],
            "list_display_links": ["name"],
            "list_filter": ["is_vip"],
            "result_count": 1,
            "full_result_count": 1,
            "list_editable": ["is_vip"],

            actions_list = [
                ['delete_selected', 'delete selected authors'],
                ['make_old', 'make all others old']
            ]

            filters: [
                {'name' : 'is_vip', 'choices': ['All', 'Yes', 'No']}
            ],

            editing_fields: {
                "name": {
                    "name":"name",
                    "type": "CharField",
                    "attrs": {},
                }
            }
        },

        "change_list": {
            "columns": [
                    {"field": "name", "headerName" "name"},
                    {"field": "age", "headerName": "age"},
                    {"field": "is_vip"", "headerName":"is_this_author_a_vip"}
                ],

            "rows": [
                {
                    'id': 1,
                    'change_url': 'https://localhost:8000/api_admin/authors/1/change/',
                    'cells': {
                        "name": "muhammad",
                        "age": 20,
                        "vip": false
                    }
                }
            ],
        }
    }
    """
    permission_classes = []

    def get(self, request, model_admin):
        try:
            cl = model_admin.get_changelist_instance(request)
        except IncorrectLookupParameters as e:
            raise NotFound(str(e))
        columns = self.get_columns(request, cl)
        rows = self.get_rows(request, cl)
        config = self.get_config(request, cl)
        return Response({'config': config, 'columns': columns, 'rows': rows},
                        status=status.HTTP_200_OK)

    def get_columns(self, request, cl):
        """
        return changelist columns or headers.
        """
        columns = []
        for field_name in self.get_fields_list(request, cl):
            text, _ = label_for_field(
                field_name, cl.model, model_admin=cl.model_admin, return_attr=True)
            columns.append({'field': field_name, 'headerName': text})
        return columns

    def get_rows(self, request, cl):
        """
        Return changelist rows actual list of data.
        """
        rows = []
        # generate changelist attributes (e.g result_list, paginator, result_count)
        cl.get_results(request)
        empty_value_display = cl.model_admin.get_empty_value_display()
        for result in cl.result_list:
            model_info = (cl.model_admin.admin_site.name, type(
                result)._meta.app_label, type(result)._meta.model_name)
            row = {
                'change_url': reverse('%s:%s_%s_change' % model_info, kwargs={'object_id': result.pk}, request=request),
                'id': result.pk,
                'cells': {}
            }

            for field_name in self.get_fields_list(request, cl):
                try:
                    _, _, value = lookup_field(
                        field_name, result, cl.model_admin)

                    # if the value is a Model instance get the string representation
                    if value and isinstance(value, Model):
                        result_repr = str(value)
                    else:
                        result_repr = value

                    # if there are choices display the choice description string instead of the value
                    try:
                        model_field = result._meta.get_field(field_name)
                        choices = getattr(model_field, 'choices', None)
                        if choices:
                            result_repr = [
                                choice for choice in choices if choice[0] == value
                            ][0][1]
                    except FieldDoesNotExist:
                        pass

                    # if the value is null set result_repr to empty_value_display
                    if value == None:
                        result_repr = empty_value_display

                except ObjectDoesNotExist:
                    result_repr = empty_value_display

                row['cells'][field_name] = result_repr
            rows.append(row)
        return rows

    def get_config(self, request, cl):
        config = {}

        # add the ModelAdmin attributes that the changelist uses
        for option_name in cl.model_admin.changelist_options:
            config[option_name] = (getattr(cl.model_admin, option_name, None))

        # changelist pagination attributes
        config['full_count'] = cl.full_result_count
        config['result_count'] = cl.result_count

        # a list of action names and choices
        config['action_choices'] = cl.model_admin.get_action_choices(
            request, [])

        # a list of filters titles and choices
        filters_spec, _, _, _, _ = cl.get_filters(request)
        if filters_spec:
            config['filters'] = [
                {"title": filter.title, "choices": filter.choices(cl)} for filter in filters_spec]
        else:
            config['filters'] = []

        # a list of fields that you can sort with
        list_display_fields = []
        for field_name in self.get_fields_list(request, cl):
            try:
                cl.model._meta.get_field(field_name)
                list_display_fields.append(field_name)
            except FieldDoesNotExist:
                pass
        config['list_display_fields'] = list_display_fields

        # a dict of serializer fields attributes for every field in list editable
        editing_fields = {}
        serializer_class = cl.model_admin.get_serializer_class(
            request, changelist=True)
        serializer = serializer_class()
        form_fields = get_form_fields(serializer)

        for field in form_fields:
            if field['name'] in cl.list_editable:
                editing_fields[field['name']] = field

        config['editing_fields'] = editing_fields

        return config

    def get_fields_list(self, request, cl):
        list_display = cl.model_admin.get_list_display(request)
        exclude = cl.model_admin.exclude or tuple()
        fields_list = tuple(
            filter(lambda item: item not in exclude, list_display))
        return fields_list


class HandleActionView(APIView):
    """
        Preform admin actions using json.
        json object would look like:
        {
        action: 'delete_selected',
        selected_ids: [
                1,
                2,
                3
            ],
        select_across: false
        }
    """
    permission_classes = []
    serializer_class = None

    def get(self, request, admin):
        serializer = self.serializer_class()
        form_fields = get_form_fields(serializer)
        return Response({'fields': form_fields}, status=status.HTTP_200_OK)

    def post(self, request, model_admin):
        serializer = self.serializer_class(data=request.data)
        # validate the action selected
        if serializer.is_valid():
            # preform the action on the selected items
            action = serializer.validated_data.get('action')
            select_across = serializer.validated_data.get('select_across')
            func = model_admin.get_actions(request)[action][0]
            try:
                cl = model_admin.get_changelist_instance(request)
            except IncorrectLookupParameters as e:
                raise NotFound(str(e))
            queryset = cl.get_queryset(request)

            # get a list of pks of selected changelist items
            selected = request.data.get('selected_ids', None)
            if not selected and not select_across:
                msg = _("Items must be selected in order to perform "
                        "actions on them. No items have been changed.")
                return Response({'detail': msg}, status=status.HTTP_400_BAD_REQUEST)
            if not select_across:
                queryset = queryset.filter(pk__in=selected)

            # if the action returns a response
            response = func(model_admin, request, queryset)

            if response:
                return response
            else:
                msg = _("action was performed successfully")
                return Response({'detail': msg}, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class HistoryView(APIView):
    """
    History of actions that happened to this object.
    """
    permission_classes = []
    serializer_class = None

    def get(self, request, object_id, model_admin):
        from django.contrib.admin.models import LogEntry
        model = model_admin.model
        opts = model._meta
        obj = model_admin.get_object(request, unquote(object_id))

        # if the object does not exist respond with 404 response
        if obj is None:
            msg = _("%(name)s with ID “%(key)s” doesn't exist. Perhaps it was deleted?") % {
                'name': opts.verbose_name,
                'key': unquote(object_id),
            }
            return Response({'detail': msg}, status=status.HTTP_404_NOT_FOUND)

        # if user has no change permission on this model then respond permission Denied
        if not model_admin.has_view_or_change_permission(request, obj):
            raise PermissionDenied

        # Then get the history for this object.
        action_list = LogEntry.objects.filter(
            object_id=unquote(object_id),
            content_type=get_content_type_for_model(model)
        ).select_related().order_by('action_time')

        # paginate the action_list
        page = model_admin.admin_site.paginate_queryset(
            action_list, request, view=self)

        # serialize the LogEntry queryset
        serializer = self.serializer_class(page, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)
