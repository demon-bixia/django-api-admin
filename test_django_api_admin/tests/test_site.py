"""
admin site tests
"""
import json

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.http import JsonResponse
from django.urls import path, reverse

from rest_framework.renderers import JSONRenderer
from rest_framework.test import (APIRequestFactory, APITestCase,
                                 URLPatternsTestCase, force_authenticate)

from test_django_api_admin.models import Author, Book, Publisher
from django_api_admin.admins.model_admin import APIModelAdmin
from test_django_api_admin.admin import site
from django_api_admin.utils.force_login import force_login

UserModel = get_user_model()
renderer = JSONRenderer()


def author_detail_view(request, pk):
    author = Author.objects.filter(pk=pk).first()
    return JsonResponse({'name': author.name})


class APIAdminSiteTestCase(APITestCase, URLPatternsTestCase):
    urlpatterns = [
        path('api_admin/', site.urls),
        path('author/<int:pk>/', author_detail_view, name='author-detail')
    ]

    def setUp(self) -> None:
        self.factory = APIRequestFactory()

        # create a superuser
        self.user = UserModel.objects.create_superuser(username='admin')
        self.user.set_password('password')
        self.user.save()

        # authenticate the superuser
        force_login(self.client, self.user)

    def test_registering_models(self):
        from django.db import models

        class Meta:
            app_label = 'django_api_admin'

        # dynamically some create models and modelAdmins
        student_model = type("Student", (models.Model,),
                             {'__module__': __name__, 'Meta': Meta})
        teacher_model = type("Teacher", (models.Model,),
                             {'__module__': __name__, 'Meta': Meta})
        teacher_model_admin = type("TeacherModelAdmin", (APIModelAdmin,), {
                                   '__module__': __name__, 'Meta': Meta})

        # register the models using the site
        site.register(student_model)
        site.register(teacher_model, teacher_model_admin)

        # test that the models and modelAdmins are in site._registry
        self.assertIn(student_model, site._registry)
        self.assertIn(teacher_model, site._registry)
        self.assertTrue(isinstance(
            site._registry[teacher_model], APIModelAdmin))

    def test_app_list_serializable(self):
        # force superuser authentication
        request = self.factory.get('index/')
        force_authenticate(request, self.user)
        request.user = self.user
        # test if app_list can be serialized to json
        data = renderer.render(site.get_app_list(request))
        self.assertIsNotNone(data)

    def test_each_context_serializable(self):
        # force superuser authentication
        request = self.factory.get('index/')
        force_authenticate(request, self.user)
        request.user = self.user
        # test if context can be serialized to json
        data = renderer.render(site.each_context(request))
        self.assertIsNotNone(data)

    def test_index_view(self):
        # test if the index view works
        url = reverse('api_admin:index')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_app_index_view(self):
        # test if the app_index view works
        app_label = Author._meta.app_label
        url = reverse('api_admin:app_list', kwargs={'app_label': app_label})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_i18n_javascript(self):

        # test if the i18n_javascript view works
        url = reverse('api_admin:language_catalog')
        response = self.client.get(url, Accept_Language="ar")
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.data['catalog'])

    def test_permission_denied(self):
        # create a non-staff user
        user = UserModel.objects.create(username='test')
        user.set_password('password')
        user.is_staff = False
        user.save()

        force_login(self.client, user)

        # test if app_index denies permission
        app_label = Author._meta.app_label
        url = reverse('api_admin:app_list', kwargs={'app_label': app_label})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        # test if index denies permission
        url = reverse('api_admin:index')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        # test if password change denies permission
        url = reverse('api_admin:password_change')
        response = self.client.post(url, {'old_password': 'new_password', 'new_password1': 'new_password',
                                          'new_password2': 'new_password'})
        self.assertEqual(response.status_code, 403)

    def test_view_on_site_view(self):
        if site.include_view_on_site_view:
            # create an author
            Author.objects.create(name='muhammad', age=2, user=self.user)
            # test if view_on_site view works
            content_type_id = ContentType.objects.get(
                app_label=Author._meta.app_label, model=Author._meta.verbose_name).id
            object_id = Author.objects.first().id
            url = reverse('api_admin:view_on_site', kwargs={
                          'content_type_id': content_type_id, 'object_id': object_id})
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data['url'],
                             'http://testserver/author/1/')
            url = response.data['url']
            # test the detail view
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            author = json.loads(response.content)
            self.assertEqual(author['name'], 'muhammad')

    def test_api_root_view(self):
        if site.include_root_view:
            url = reverse('api_admin:api-root')
            response = self.client.get(url)

            self.assertNotEqual(response.status_code, 403)
            self.assertEqual(response.status_code, 200)

            key_found = False
            for key, value in response.data.items():
                if key == 'index':
                    key_found = True
                    break
            if not key_found:
                raise AssertionError('Site didn`t return api-root view')

    def test_each_context_view(self):
        url = reverse('api_admin:site_context')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['site_title'], 'Django site admin')

    def test_autocomplete_view(self):
        # create an author, and a book
        author = Author.objects.create(name='Muhammad', age=2, user=self.user)
        publisher = Publisher.objects.create(name='the daily blob')
        author.publisher.add(publisher)
        Book.objects.create(title='Things fall apart', author=author)

        # select a book author by searching for the author using the publisher name of the author
        url = reverse('api_admin:autocomplete')
        response = self.client.get(url, {
            'term': 'blob',
            'app_label': Author._meta.app_label,
            'model_name': Book._meta.verbose_name,
            'field_name': Author._meta.verbose_name
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]['name'], 'Muhammad')
