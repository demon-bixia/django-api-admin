import json

from django.contrib.admin.options import (TO_FIELD_VAR,
                                          IncorrectLookupParameters,
                                          get_content_type_for_model)
from django.contrib.admin.utils import label_for_field, lookup_field, unquote
from django.contrib.admin.views.autocomplete import AutocompleteJsonView
from django.contrib.auth import login, logout
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import FieldDoesNotExist, ObjectDoesNotExist
from django.db.models import Model
from django.http import JsonResponse
from django.middleware.csrf import get_token
from django.utils.translation import gettext_lazy as _
from django.views.i18n import JSONCatalog
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView

from .utils import ModelDiffHelper, get_form_fields


class CsrfTokenView(APIView):
    serializer_class = None
    permission_classes = []

    def get(self, request):
        return Response({'csrftoken': get_token(request)})


class UserInformation(APIView):
    serializer_class = None
    permission_classes = []

    def get(self, request):
        serializer = self.serializer_class(request.user)
        return Response({'user': serializer.data})


class LoginView(APIView):
    """
    Allow users to login using username and password.
    """
    serializer_class = None
    permission_classes = []

    def get(self, request, admin_site):
        serializer = self.serializer_class()
        form_fields = get_form_fields(serializer)
        return Response({'fields': form_fields}, status=status.HTTP_200_OK)

    def post(self, request, admin_site):
        serializer = self.serializer_class(
            data=request.data, context={'request': request})
        if serializer.is_valid():
            user = serializer.get_user()
            login(request, user)
            user_serializer = admin_site.user_serializer(user)
            data = {
                'detail': _('you are logged in successfully'),
                'user': user_serializer.data
            }
            return Response(data, status=status.HTTP_200_OK)

        for error in serializer.errors.get('non_field_errors', []):
            if error.code == 'permission_denied':
                return Response(serializer.errors, status=status.HTTP_403_FORBIDDEN)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    """
    Logout and display a 'you are logged out ' message.
    """
    permission_classes = []

    def post(self, request):
        logout(request)
        return Response({"detail": _("You are logged out.")}, status=status.HTTP_200_OK)

    def get(self, request):
        return self.post(request)


class PasswordChangeView(APIView):
    """
        Handle the "change password" task -- both form display and validation.
    """
    serializer_class = None
    permission_classes = []

    def post(self, request):
        serializer_class = self.serializer_class
        serializer = serializer_class(
            data=request.data, context={'user': request.user})
        if serializer.is_valid():
            serializer.save()
            return Response({'detail': _('Your password was changed')},
                            status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class IndexView(APIView):
    """
    Return json object that lists all the installed
    apps that have been registered by the admin site.
    """
    permission_classes = []

    def get(self, request, admin_site):
        app_list = admin_site.get_app_list(request)
        # add an url to app_index in every app in app_list
        for app in app_list:
            url = reverse(f'{admin_site.name}:app_list', kwargs={
                'app_label': app['app_label']}, request=request)
            app['url'] = url
        data = {
            'app_list': app_list,
        }
        request.current_app = admin_site.name
        return Response(data, status=status.HTTP_200_OK)


class AppIndexView(APIView):
    """
    Lists models inside a given app.
    """

    permission_classes = []

    def get(self, request, app_label, admin_site):
        app_dict = admin_site._build_app_dict(request, app_label)

        if not app_dict:
            return Response({'detail': _('The requested admin page does not exist.')},
                            status=status.HTTP_404_NOT_FOUND)

        # Sort the models alphabetically within each app.
        app_dict['models'].sort(key=lambda x: x['name'])

        data = {
            'app_label': app_label,
            'app': app_dict,
        }

        return Response(data, status=status.HTTP_200_OK)


class LanguageCatalogView(APIView):
    """
      Returns json object with django.contrib.admin i18n translation catalog
      to be used by a client site javascript library
    """
    permission_classes = []

    def get(self, request):
        response = JSONCatalog.as_view(packages=['django_api_admin'])(request)
        return Response(response.content, status=response.status_code)


class AutoCompleteView(APIView):
    """Handle AutocompleteWidget's AJAX requests for data."""
    permission_classes = []

    def get(self, request, admin_site):
        response = AutocompleteJsonView.as_view(admin_site=admin_site)(request)
        return Response({'content': response.content}, status=response.status_code)


class SiteContextView(APIView):
    """
    Returns the Attributes of AdminSite class (e.g. site_title, site_header)
    """
    permission_classes = []

    def get(self, request, admin_site):
        context = admin_site.each_context(request)
        return Response(context, status=status.HTTP_200_OK)


class AdminLogView(APIView):
    """
    Returns a list of actions that were preformed using django admin.
    """
    serializer_class = None
    pagination_class = None
    permission_classes = []
    ordering_fields = ['action_time', '-action_time']

    def get(self, request, admin_site):
        from django.contrib.admin.models import LogEntry

        queryset = LogEntry.objects.all()

        # order the queryset
        try:
            ordering = self.request.query_params.get('o')
            if ordering is not None:
                if ordering not in self.ordering_fields:
                    raise KeyError
                queryset = queryset.order_by(ordering)
        except:
            return Response({'detail': 'Wrong ordering field set.'}, status=status.HTTP_400_BAD_REQUEST)

        # filter the queryset.
        try:
            object_id = self.request.query_params.get('object_id')
            if object_id is not None:
                queryset = queryset.filter(object_id=object_id)
        except:
            return Response({'detail': 'Bad filters.'}, status=status.HTTP_400_BAD_REQUEST)

        # paginate queryset.
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(queryset, request, view=self)

        # serialize queryset.
        serializer = self.serializer_class(page, many=True)

        return Response({
            'action_list': self.serialize_messages(serializer.data),
            'config': self.get_config(page, queryset)},
            status=status.HTTP_200_OK)

    def serialize_messages(self, data):
        for idx, item in enumerate(data, start=0):
            data[idx]['change_message'] = json.loads(
                item['change_message'] or '[]')
        return data

    def get_config(self, page, queryset):
        return {
            'result_count': len(page),
            'full_result_count': queryset.count(),
        }


class AdminAPIRootView(APIView):
    """
    A list of all root urls in django_api_admin
    """
    root_urls = None

    def get(self, request, *args, **kwargs):
        namespace = request.resolver_match.namespace
        data = dict()

        for url in self.root_urls:
            if request.user.is_authenticated and url.name == 'login':
                continue
            elif not request.user.is_authenticated and url.name in ('logout', 'password_change'):
                continue
            data[url.name] = reverse(
                namespace + ':' + url.name, request=request, args=args, kwargs=kwargs)

        return Response(data or {}, status=status.HTTP_200_OK)


# model admin wide views
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

        if admin.is_inline:
            info = (
                admin.admin_site.name, admin.parent_model._meta.app_label,
                admin.parent_model._meta.model_name, admin.opts.app_label,
                admin.opts.model_name
            )
            pattern = '%s:%s_%s_%s_%s_detail'
        else:
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
        if not admin.is_inline:
            # validate the reverse to field reference
            to_field = request.query_params.get(TO_FIELD_VAR)
            if to_field and not admin.to_field_allowed(request, to_field):
                return Response({'detail': 'The field %s cannot be referenced.' % to_field},
                                status=status.HTTP_400_BAD_REQUEST)
            obj = admin.get_object(request, unquote(object_id), to_field)
        else:
            obj = admin.get_object(request, unquote(object_id))

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
        if not admin.is_inline:
            info = (
                admin.admin_site.name,
                admin.model._meta.app_label,
                admin.model._meta.model_name,
            )
            pattern = '%s:%s_%s_'
            data['history_url'] = reverse((pattern + 'history') % info, kwargs={'object_id': data['pk']},
                                          request=request)
            if admin.view_on_site:
                model_type = ContentType.objects.get(app_label=admin.opts.app_label,
                                                     model=admin.model._meta.verbose_name)
                data['view_on_site'] = reverse('%s:view_on_site' % admin.admin_site.name,
                                               kwargs={
                                                   'content_type_id': model_type.pk, 'object_id': obj.pk},
                                               request=request)
        else:
            info = (
                admin.admin_site.name, admin.parent_model._meta.app_label,
                admin.parent_model._meta.model_name, admin.opts.app_label,
                admin.opts.model_name
            )
            pattern = '%s:%s_%s_%s_%s_'

        data['list_url'] = reverse((pattern + 'list') % info, request=request)
        data['delete_url'] = reverse(
            (pattern + 'delete') % info, kwargs={'object_id': data['pk']}, request=request)
        data['change_url'] = reverse(
            (pattern + 'change') % info, kwargs={'object_id': data['pk']}, request=request)
        return Response(data, status=status.HTTP_200_OK)


class AddView(APIView):
    """
    Add new instances of this model.
    """
    serializer_class = None
    permission_classes = []

    def get(self, request, model_admin):
        data = dict()
        serializer = self.serializer_class()
        data['fields'] = get_form_fields(serializer)
        data['config'] = self.get_config(model_admin)

        if not model_admin.is_inline:
            data['inlines'] = self.get_inlines(request, model_admin)

        return Response(data, status=status.HTTP_200_OK)

    def post(self, request, model_admin):
        # if the user doesn't have added permission respond with permission denied
        if not model_admin.has_add_permission(request):
            raise PermissionDenied

        # validate data and send
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            opts = model_admin.model._meta
            new_object = serializer.save()

            if model_admin.is_inline:
                parent_model = model_admin.parent_model
                change_object = parent_model.objects.get(
                    **{new_object._meta.verbose_name: new_object})
                model_admin = model_admin.admin_site._registry.get(
                    parent_model)
            else:
                model_admin = model_admin
                change_object = new_object

            # log addition of the new instance
            model_admin.log_addition(request, change_object, [{'added': {
                'name': str(new_object._meta.verbose_name),
                'object': str(new_object),
            }}])
            msg = _(
                f'The {opts.verbose_name} “{str(new_object)}” was added successfully.')
            return Response({'data': serializer.data, 'detail': msg}, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def get_config(self, model_admin):
        config = {}

        for option_name in model_admin.form_options:
            config[option_name] = getattr(
                model_admin, option_name, None
            )

        return config

    def get_inlines(self, request,  model_admin):
        inlines = list()

        for inline_admin in model_admin.get_inline_instances(request, obj=None):
            serializer_class = inline_admin.get_serializer_class(request)
            serializer = serializer_class()
            inlines.append(
                {
                    'name': inline_admin.model._meta.verbose_name_plural,
                    'object_name': inline_admin.model._meta.verbose_name,
                    'admin_name':  inline_admin.parent_model._meta.app_label + '_' + inline_admin.parent_model._meta.model_name + '_' + inline_admin.model._meta.model_name,
                    'url': self.get_inline_add_url(request, inline_admin),
                    'fields': get_form_fields(serializer),
                    'config': self.get_config(inline_admin)
                }
            )

        return inlines

    def get_inline_add_url(self,  request, inline_admin):
        info = (inline_admin.admin_site.name, inline_admin.parent_model._meta.app_label,
                inline_admin.parent_model._meta.model_name,
                inline_admin.opts.app_label, inline_admin.opts.model_name)
        return reverse('%s:%s_%s_%s_%s_add' % info, request=request)


class ChangeView(APIView):
    """
    Change an existing instance of this model.
    """
    serializer_class = None
    permission_classes = []

    def get_serializer_instance(self, request, obj):
        serializer = None

        if request.method == 'PATCH':
            serializer = self.serializer_class(
                instance=obj, data=request.data, partial=True)

        elif request.method == 'PUT':
            serializer = self.serializer_class(instance=obj, data=request.data)

        elif request.method == 'GET':
            serializer = self.serializer_class(instance=obj)

        return serializer

    def update(self, request, object_id, admin):
        if not admin.is_inline:
            # validate the reverse to field reference
            to_field = request.query_params.get(TO_FIELD_VAR)
            if to_field and not admin.to_field_allowed(request, to_field):
                return Response({'detail': 'The field %s cannot be referenced.' % to_field},
                                status=status.HTTP_400_BAD_REQUEST)
            obj = admin.get_object(request, unquote(object_id), to_field)
        else:
            obj = admin.get_object(request, unquote(object_id))

        opts = admin.model._meta
        helper = ModelDiffHelper(obj)

        # if the object doesn't exist respond with not found
        if obj is None:
            msg = _("%(name)s with ID “%(key)s” doesn't exist. Perhaps it was deleted?") % {
                'name': admin.model._meta.verbose_name,
                'key': unquote(object_id),
            }
            return Response({'detail': msg}, status=status.HTTP_404_NOT_FOUND)

        # test user change permission in this model.
        if not admin.has_change_permission(request, obj):
            raise PermissionDenied

        # initiate the serializer based on the request method
        serializer = self.get_serializer_instance(request, obj)

        # if the method is get return the change form fields dictionary
        if request.method == 'GET':
            data = dict()

            data['fields'] = get_form_fields(serializer, change=True)

            data['config'] = self.get_config(admin)

            return Response(data, status=status.HTTP_200_OK)

        # update and log the changes to the object
        if serializer.is_valid():
            updated_object = serializer.save()

            if admin.is_inline:
                parent_model = admin.parent_model
                model_admin = admin.admin_site._registry.get(parent_model)
                changed_object = parent_model.objects.get(
                    **{updated_object._meta.verbose_name: updated_object})
            else:
                model_admin = admin
                changed_object = updated_object

            # log the change of  change
            model_admin.log_change(request, changed_object, [{'changed': {
                'name': str(updated_object._meta.verbose_name),
                'object': str(updated_object),
                'fields': helper.set_changed_model(updated_object).changed_fields
            }}])
            msg = _(
                f'The {opts.verbose_name} “{str(updated_object)}” was changed successfully.')
            return Response({'data': serializer.data, 'detail': msg}, status=status.HTTP_200_OK)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, object_id, admin):
        return self.update(request, object_id, admin)

    def patch(self, request, object_id, admin):
        return self.update(request, object_id, admin)

    def get(self, request, object_id, admin):
        return self.update(request, object_id, admin)

    def get_config(self, model_admin):
        config = {}

        for option_name in model_admin.form_options:
            config[option_name] = getattr(
                model_admin, option_name, None
            )

        return config


class DeleteView(APIView):
    """
    Delete a single object from this model
    """
    permission_classes = []

    def delete(self, request, object_id, admin):
        opts = admin.model._meta

        if not admin.is_inline:
            # validate the reverse to field reference.
            to_field = request.query_params.get(TO_FIELD_VAR)
            if to_field and not admin.to_field_allowed(request, to_field):
                return Response({'detail': 'The field %s cannot be referenced.' % to_field},
                                status=status.HTTP_400_BAD_REQUEST)
            obj = admin.get_object(request, unquote(object_id), to_field)
        else:
            obj = admin.get_object(request, unquote(object_id))

        if obj is None:
            msg = _("%(name)s with ID “%(key)s” doesn't exist. Perhaps it was deleted?") % {
                'name': opts.verbose_name,
                'key': unquote(object_id),
            }
            return Response({'detail': msg}, status=status.HTTP_404_NOT_FOUND)

        # check delete object permission
        if not admin.has_delete_permission(request, obj):
            raise PermissionDenied

        model_admin = admin if not admin.is_inline else admin.admin_site._registry.get(
            admin.parent_model)

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
