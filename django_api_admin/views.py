from django.contrib.admin.options import IncorrectLookupParameters, TO_FIELD_VAR, get_content_type_for_model
from django.contrib.admin.utils import label_for_field, lookup_field, unquote
from django.contrib.admin.views.autocomplete import AutocompleteJsonView
from django.contrib.auth import login, logout
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Model
from django.utils.translation import gettext_lazy as _
from django.views.i18n import JSONCatalog
from rest_framework import status
from rest_framework.exceptions import NotFound, PermissionDenied
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView

from .utils import ModelDiffHelper


# admin-site-wide views
class LoginView(APIView):
    """
    Allow users to login using username and password
    """
    serializer_class = None
    permission_classes = []

    def post(self, request):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        if serializer.is_valid():
            login(request, serializer.get_user())
            msg = _('you are logged in successfully')
            return Response({'detail': msg},
                            status=status.HTTP_200_OK)

        for error in serializer.errors.get('non_field_errors', []):
            if error.code == 'permission_denied':
                return Response(serializer.errors, status=status.HTTP_403_FORBIDDEN)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    """
    Logout and display a 'your are logged out ' message.
    """
    permission_classes = []

    def post(self, request):
        message = _("You are logged out.")
        logout(request)
        return Response({'detail': message},
                        status=status.HTTP_200_OK)

    def get(self, *args, **kwargs):
        return self.post(*args, **kwargs)


class PasswordChangeView(APIView):
    """
        Handle the "change password" task -- both form display and validation.
    """
    serializer_class = None
    permission_classes = []

    def post(self, request):
        serializer_class = self.serializer_class
        serializer = serializer_class(data=request.data, context={'user': request.user})
        if serializer.is_valid():
            serializer.save()
            return Response({'detail': _('Your password was changed')},
                            status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class IndexView(APIView):
    """
    Return json object that lists all of the installed
    apps that have been registered by the admin site.
    """
    permission_classes = []

    def get(self, request, admin_site):
        app_list = admin_site.get_app_list(request)
        # add a url to app_index in every app in app_list
        for app in app_list:
            url = reverse(f'{admin_site.name}:app_list', kwargs={'app_label': app['app_label']}, request=request)
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
    Returns the Attributes of AdminSite class (e.g site_title, site_header)
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
    permission_classes = []

    def get(self, request, admin_site):
        from django.contrib.admin.models import LogEntry
        page = admin_site.paginate_queryset(LogEntry.objects.all(), request, view=self)
        serializer = self.serializer_class(page, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


# todo clean browsable api urls based on how client uses them
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
            data[url.name] = reverse(namespace + ':' + url.name, request=request, args=args, kwargs=kwargs)

        return Response(data or {}, status=status.HTTP_200_OK)


# model admin wide views
class AdminContextView(APIView):
    """
    List of options defined in the model_admin class.
    """
    permission_classes = []

    def get(self, request, admin):
        data = dict()
        data['permission_map'] = admin.get_permission_map(request)
        data['options'] = admin.get_admin_options(request)
        if not admin.is_inline:
            data['inlines'] = admin.get_inlines_list(request)
        return Response(data, status=status.HTTP_200_OK)


class ChangeListView(APIView):
    """
    Return a json object representing the django admin changelist table.
    supports querystring filtering, pagination and search also changes based on list display.
    Note: this is different from the list all objects view.
    example returned json:

    {
        'columns': [{'name': 'name'}, {'age': 'age'}, {'is_vip': 'is_this_author_a_vip'},],
        'rows': [
            {
                'name': 'muhammad',
                'age': 20,
                'vip': false
            }
        ],
        'result_count': 1,
        'full_result_count: 1
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
        return Response({'columns': columns, 'rows': rows, 'full_result_count': cl.full_result_count,
                         'result_count': cl.result_count},
                        status=status.HTTP_200_OK)

    def get_columns(self, request, cl):
        """
        return changelist columns or headers.
        """
        columns = []
        for field_name in cl.model_admin.list_display:
            text, _ = label_for_field(field_name, cl.model, model_admin=cl.model_admin, return_attr=True)
            columns.append({field_name: text})
        return columns

    def get_rows(self, request, cl):
        """
        Return changelist rows actual list of data.
        """
        rows = []
        # generate changelist attributes (e.g result_list, paginator, result_count)
        cl.get_results(request)
        empty_value_display = cl.model_admin.get_empty_value_display
        for result in cl.result_list:
            row = {}
            for field_name in cl.model_admin.list_display:
                try:
                    _, _, value = lookup_field(field_name, result, cl.model_admin)
                    # if the value is a Model instance get the string representation
                    if value and isinstance(value, Model):
                        result_repr = str(value)
                    else:
                        result_repr = value
                except ObjectDoesNotExist:
                    result_repr = empty_value_display
                row[field_name] = result_repr
            rows.append(row)
        return rows


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
            item['detail_url'] = reverse(pattern % info, kwargs={'object_id': int(item['pk'])}, request=request)
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
                                               kwargs={'content_type_id': model_type.pk, 'object_id': obj.pk},
                                               request=request)
        else:
            info = (
                admin.admin_site.name, admin.parent_model._meta.app_label,
                admin.parent_model._meta.model_name, admin.opts.app_label,
                admin.opts.model_name
            )
            pattern = '%s:%s_%s_%s_%s_'

        data['list_url'] = reverse((pattern + 'list') % info, request=request)
        data['delete_url'] = reverse((pattern + 'delete') % info, kwargs={'object_id': data['pk']}, request=request)
        data['change_url'] = reverse((pattern + 'change') % info, kwargs={'object_id': data['pk']}, request=request)
        return Response(data, status=status.HTTP_200_OK)


class AddView(APIView):
    """
    Add new instances of this model.
    """
    serializer_class = None
    permission_classes = []

    def get(self, request, admin):
        serializer = self.serializer_class()
        form_fields = admin.get_form_fields(serializer)
        return Response({'form': {'fields': form_fields}}, status=status.HTTP_200_OK)

    def post(self, request, admin):
        # if the user doesn't have add permission respond with permission denied
        if not admin.has_add_permission(request):
            raise PermissionDenied

        # validate data and send
        serializer = self.serializer_class(data=request.data)
        if serializer.is_valid():
            opts = admin.model._meta
            new_object = serializer.save()

            if admin.is_inline:
                parent_model = admin.parent_model
                change_object = parent_model.objects.get(**{new_object._meta.verbose_name: new_object})
                model_admin = admin.admin_site._registry.get(parent_model)
            else:
                model_admin = admin
                change_object = new_object

            # log addition of the new instance
            model_admin.log_addition(request, change_object, [{'added': {
                'name': str(new_object._meta.verbose_name),
                'object': str(new_object),
            }}])
            msg = _(f'The {opts.verbose_name} “{str(new_object)}” was added successfully.')
            return Response({opts.verbose_name: serializer.data, 'detail': msg}, status=status.HTTP_201_CREATED)
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ChangeView(APIView):
    """
    Change an existing instance of this model.
    """
    serializer_class = None
    permission_classes = []

    def get_serializer_instance(self, request, obj):
        if request.method == 'PATCH':
            return self.serializer_class(instance=obj, data=request.data, partial=True)
        return self.serializer_class(instance=obj, data=request.data)

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
            form_fields = admin.get_form_fields(serializer, change=True)
            return Response({'form': {'fields': form_fields}}, status=status.HTTP_200_OK)

        # update and log the changes to the object
        if serializer.is_valid():
            updated_object = serializer.save()

            if admin.is_inline:
                parent_model = admin.parent_model
                model_admin = admin.admin_site._registry.get(parent_model)
                changed_object = parent_model.objects.get(**{updated_object._meta.verbose_name: updated_object})
            else:
                model_admin = admin
                changed_object = updated_object

            # log the change of  change
            model_admin.log_change(request, changed_object, [{'changed': {
                'name': str(updated_object._meta.verbose_name),
                'object': str(updated_object),
                'fields': helper.set_changed_model(updated_object).changed_fields
            }}])
            msg = _(f'The {opts.verbose_name} “{str(updated_object)}” was changed successfully.')
            return Response({opts.verbose_name: serializer.data, 'detail': msg})
        else:
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, object_id, admin):
        return self.update(request, object_id, admin)

    def patch(self, request, object_id, admin):
        return self.update(request, object_id, admin)

    def get(self, request, object_id, admin):
        return self.update(request, object_id, admin)


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

        model_admin = admin if not admin.is_inline else admin.admin_site._registry.get(admin.parent_model)

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
            # actions should always return a Response
            return func(model_admin, request, queryset)
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
        page = model_admin.admin_site.paginate_queryset(action_list, request, view=self)

        # serialize the LogEntry queryset
        serializer = self.serializer_class(page, many=True)

        return Response(serializer.data, status=status.HTTP_200_OK)
