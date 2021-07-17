from django.apps import apps
from django.contrib.auth import login, logout
from django.contrib.contenttypes.models import ContentType
from django.contrib.sites.shortcuts import get_current_site
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import gettext_lazy as _
from django.views.i18n import JSONCatalog
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView
from rest_framework import exceptions


class APIRootView(APIView):
    """
    An optional Root endpoint for the django_api_admin app
    """
    def get(self, request, site, format=None):
        app_labels = [model._meta.app_label for model, model_admin in site._registry.items()]

        data = {
            'index': reverse('api_admin:index', request=request, format=format),
            'apps': [reverse('api_admin:app_list', kwargs={'app_label': app_label}, request=request, format=format) for
                     app_label in app_labels],
        }

        data.update({
            'password_change': reverse('api_admin:password_change', request=request, format=format),
            'logout': reverse('api_admin:logout', request=request, format=format)
        }) if request.user.is_authenticated else data.update({
            'login': reverse('api_admin:login', request=request, format=format),
        })

        return Response(data, status=status.HTTP_200_OK)


class LoginView(APIView):
    """
    Allow users to login using username and password
    """

    serializer_class = None
    user_serializer_class = None

    def post(self, request, extra_context=None):
        serializer = self.serializer_class(data=request.data, context={'request': request})
        if serializer.is_valid():
            login(request, serializer.get_user())
            user_serializer = self.user_serializer_class(request.user)
            return Response({'user': user_serializer.data, **(extra_context or {})}, status=status.HTTP_200_OK)

        for error in serializer.errors['non_field_errors']:
            if error.code == 'permission_denied':
                return Response(serializer.errors, status=status.HTTP_403_FORBIDDEN)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    """
    logout and display a 'your are logged out ' message.
    """
    user_serializer_class = None

    def get(self, request, extra_context=None):
        user_serializer = self.user_serializer_class(request.user)
        message = _("You are logged out.")
        logout(request)
        return Response({'user': user_serializer.data, 'message': message, **(extra_context or {})},
                        status=status.HTTP_200_OK)

    def post(self, request, extra_context=None):
        return self.get(request, extra_context)


class PasswordChangeView(APIView):
    """
        Handle the "change password" task -- both form display and validation.
    """
    serializer_class = None

    def post(self, request, extra_context=None):
        serializer = self.serializer_class(data=request.data, context={'user': request.user})
        if serializer.is_valid():
            serializer.save()
            return Response({'message': _('Your password was changed'), **(extra_context or {})},
                            status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class IndexView(APIView):
    """
    Return json object that lists all of the installed
    apps that have been registered by the admin site.
    """

    def get(self, request, admin_site, extra_context=None):
        app_list = admin_site.get_app_list(request)

        data = {
            **admin_site.each_context(request),
            'app_list': app_list,
            **(extra_context or {}),
        }

        request.current_app = admin_site.name

        return Response(data, status=status.HTTP_200_OK)


class AppIndexView(APIView):
    """
    Lists models inside a given app.
    """
    def get(self, request, admin_site, app_label, extra_context=None):
        app_dict = admin_site._build_app_dict(request, app_label)

        if not app_dict:
            return Response({'message': 'The requested admin page does not exist.'}, status=status.HTTP_404_NOT_FOUND)

        # Sort the models alphabetically within each app.
        app_dict['models'].sort(key=lambda x: x['name'])
        data = {
            **admin_site.each_context(request),
            'app_list': [app_dict],
            'app_label': app_label,
            **(extra_context or {}),
        }

        return Response(data, status=status.HTTP_200_OK)


class TranslationCatalogView(APIView):
    """
    Returns json object with django.contrib.admin i18n translation catalog
    to be used by a client site javascript library
    """
    def get(self, request, packages):
        response = JSONCatalog.as_view(packages=packages)(request)
        return Response({'context': response.content}, status=status.HTTP_200_OK)


class ViewOnSiteView(APIView):
    """
    Returns a json object with a url attribute that contains the
    object's detail view url.
    """

    def get(self, request, content_type_id, object_id):
        # Look up the object, making sure it's got a get_absolute_url() function.
        try:
            content_type = ContentType.objects.get(pk=content_type_id)
            if not content_type.model_class():
                raise exceptions.NotFound(_("Content type %(ct_id)s object has no associated model") %
                                          {'ct_id': content_type_id})
            obj = content_type.get_object_for_this_type(pk=object_id)
        except (ObjectDoesNotExist, ValueError):
            raise exceptions.NotFound(
                _('Content type %(ct_id)s object %(obj_id)s doesn’t exist') %
                {'ct_id': content_type_id, 'obj_id': object_id}
            )
        try:
            get_absolute_url = obj.get_absolute_url
        except AttributeError:
            raise exceptions.NotFound(
                _('%(ct_name)s objects don’t have a get_absolute_url() method') %
                {'ct_name': content_type.name}
            )

        absurl = get_absolute_url()

        # If the object actually defines a domain, we're done.
        if absurl.startswith(('http://', 'https://', '//')):
            return Response({'url': absurl}, status=status.HTTP_200_OK)

        # relation to the Site object
        try:
            object_domain = get_current_site(request).domain
        except ObjectDoesNotExist:
            object_domain = None

        if apps.is_installed('django.contrib.sites'):
            Site = apps.get_model('sites.Site')
            opts = obj._meta

            for field in opts.many_to_many:
                # Look for a many-to-many relationship to Site.
                if field.remote_field.model is Site:
                    site_qs = getattr(obj, field.name).all()
                    if object_domain and site_qs.filter(domain=object_domain).exists():
                        # The current site's domain matches a site attached to the
                        # object.
                        break
                    # Caveat: In the case of multiple related Sites, this just
                    # selects the *first* one, which is arbitrary.
                    site = site_qs.first()
                    if site:
                        object_domain = site.domain
                        break
            else:
                # No many-to-many relationship to Site found. Look for a
                # many-to-one relationship to Site.
                for field in obj._meta.fields:
                    if field.remote_field and field.remote_field.model is Site:
                        try:
                            site = getattr(obj, field.name)
                        except Site.DoesNotExist:
                            continue
                        if site is not None:
                            object_domain = site.domain
                            break

        # If all that malarkey found an object domain, use it. Otherwise, fall back
        # to whatever get_absolute_url() returned.
        if object_domain is not None:
            protocol = request.scheme
            return Response({'url': '%s://%s%s' % (protocol, object_domain, absurl)}, status=status.HTTP_200_OK)
        else:
            return Response({'url': absurl}, status=status.HTTP_200_OK)
