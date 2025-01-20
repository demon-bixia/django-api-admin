from django.utils.translation import gettext_lazy as _
from django.utils.text import capfirst

from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.exceptions import NotFound

from django_api_admin.utils.get_form_fields import get_form_fields


class IncorrectLookupParameters(Exception):
    pass


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

    def get(self):
        serializer = self.serializer_class()
        form_fields = get_form_fields(serializer)
        return Response({'fields': form_fields}, status=status.HTTP_200_OK)

    def post(self, request, model_admin):
        self.model_admin = model_admin

        serializer = self.serializer_class(data=request.data)
        # validate the action selected
        if serializer.is_valid():
            # preform the action on the selected items
            action = serializer.validated_data.get('action')
            select_across = serializer.validated_data.get('select_across')
            func = self.get_actions(request)[action][0]
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

    def get_actions(self, request):
        """
        Return a dictionary mapping the names of all actions for this
        ModelAdmin to a tuple of (callable, name, description) for each action.
        """
        # If self.actions is set to None that means actions are disabled on
        # this page.
        if self.model_admin.actions is None:
            return {}
        actions = self._filter_actions_by_permissions(
            request, self._get_base_actions())
        return {name: (func, name, desc) for func, name, desc in actions}

    def _filter_actions_by_permissions(self, request, actions):
        """Filter out any actions that the user doesn't have access to."""
        filtered_actions = []
        for action in actions:
            callable = action[0]
            if not hasattr(callable, "allowed_permissions"):
                filtered_actions.append(action)
                continue
            permission_checks = (
                getattr(self.model_admin, "has_%s_permission" % permission)
                for permission in callable.allowed_permissions
            )
            if any(has_permission(request) for has_permission in permission_checks):
                filtered_actions.append(action)
        return filtered_actions

    def _get_base_actions(self):
        """Return the list of actions, prior to any request-based filtering."""
        actions = []
        base_actions = (self.get_action(action)
                        for action in self.model_admin.actions or [])
        # get_action might have returned None, so filter any of those out.
        base_actions = [action for action in base_actions if action]
        base_action_names = {name for _, name, _ in base_actions}

        # Gather actions from the admin site first
        for name, func in self.model_admin.admin_site.actions:
            if name in base_action_names:
                continue
            description = getattr(func, "short_description",
                                  capfirst(name.replace("_", " ")))
            actions.append((func, name, description))

        # Add actions from this ModelAdmin.
        actions.extend(base_actions)
        return actions

    def get_action(self, action):
        """
        Return a given action from a parameter, which can either be a callable,
        or the name of a method on the ModelAdmin.  Return is a tuple of
        (callable, name, description).
        """
        # If the action is a callable, just use it.
        if callable(action):
            func = action
            action = action.__name__

        # Next, look for a method. Grab it off self.__class__ to get an unbound
        # method instead of a bound one; this ensures that the calling
        # conventions are the same for functions and methods.
        elif hasattr(self.model_admin.__class__, action):
            func = getattr(self.model_admin.__class__, action)

        # Finally, look for a named method on the admin site
        else:
            try:
                func = self.model_admin.admin_site.get_action(action)
            except KeyError:
                return None

        description = getattr(func, "short_description",
                              capfirst(action.replace("_", " ")))
        return func, action, description
