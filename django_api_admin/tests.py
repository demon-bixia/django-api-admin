import json

from django.contrib.auth import get_user_model
from django.contrib.contenttypes.models import ContentType
from django.http import JsonResponse
from django.urls import path, reverse
from rest_framework.parsers import JSONParser
from rest_framework.renderers import JSONRenderer
from rest_framework.test import (APIRequestFactory, APITestCase,
                                 URLPatternsTestCase, force_authenticate)

from .models import Author, Book, Publisher
from .options import APIModelAdmin
from .sites import site

UserModel = get_user_model()
renderer = JSONRenderer()
parser = JSONParser()


class AuthenticationTestCase(APITestCase, URLPatternsTestCase):
    urlpatterns = [
        path('api_admin/', site.urls),
    ]

    def setUp(self) -> None:
        self.admin_user = UserModel.objects.create_superuser(username='admin')
        self.admin_user.set_password('password')
        self.admin_user.save()

    def test_non_staff_user_login(self):
        user = UserModel.objects.create(username='test')
        user.set_password('password')
        user.save()

        url = reverse('api_admin:login')
        response = self.client.post(
            url, {'username': user.username, 'password': 'password'})
        self.assertEqual(response.status_code, 403)

    def test_staff_user_login(self):
        url = reverse('api_admin:login')
        response = self.client.post(
            url, {'username': self.admin_user.username, 'password': 'password'})
        self.assertEqual(response.status_code, 200)

    def test_access_to_login(self):
        user = UserModel.objects.create(username='test')
        user.set_password('password')
        user.save()

        url = reverse('api_admin:login')
        response = self.client.get(url)
        self.assertNotEqual(response.status_code, 403)

    def test_logout_user_logged_in(self):
        self.client.force_login(user=self.admin_user)
        url = reverse('api_admin:logout')
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.data.get('detail', None))

    def test_password_change(self):
        url = reverse('api_admin:password_change')
        self.client.force_login(user=self.admin_user)
        response = self.client.post(url, {'old_password': 'password', 'new_password1': 'new_password',
                                          'new_password2': 'new_password'})
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.data.get('detail', None))

    def test_password_change_password_mismatch(self):
        url = reverse('api_admin:password_change')
        self.client.force_login(user=self.admin_user)
        response = self.client.post(url, {'old_password': 'password', 'new_password1': 'something',
                                          'new_password2': 'something else'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.data['non_field_errors'][0].code, 'password_mismatch')


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
        self.client.force_login(self.user)

    def test_registering_models(self):
        from django.db import models

        # dynamically some create models and modelAdmins
        student_model = type("Student", (models.Model,),
                             {'__module__': __name__})
        teacher_model = type("Teacher", (models.Model,),
                             {'__module__': __name__})
        teacher_model_admin = type("TeacherModelAdmin", (APIModelAdmin,), {
                                   '__module__': __name__})

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
        data = json.loads(response.data)

    def test_permission_denied(self):
        # create a non-staff user
        user = UserModel.objects.create(username='test')
        user.set_password('password')
        user.is_staff = False
        user.save()

        self.client.force_login(user)

        # test if app_index denies permission
        app_label = Author._meta.app_label
        url = reverse('api_admin:app_list', kwargs={'app_label': app_label})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        # test if index denies permission
        url = reverse('api_admin:index')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        # test if logout denies permission
        url = reverse('api_admin:logout')
        response = self.client.post(url)
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
                app_label='django_api_admin', model='author').id
            object_id = Author.objects.first().id
            url = reverse('api_admin:view_on_site', kwargs={
                          'content_type_id': content_type_id, 'object_id': object_id})
            response = self.client.get(url)
            self.assertEqual(response.status_code, 302)
            self.assertEqual(response.get('location'),
                             'http://testserver/author/1/')
            url = response.get('location')
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


class ModelAdminTestCase(APITestCase, URLPatternsTestCase):
    urlpatterns = [
        path('api_admin/', site.urls),
    ]

    def setUp(self) -> None:
        self.factory = APIRequestFactory()

        # create a superuser
        self.user = UserModel.objects.create_superuser(username='admin')
        self.user.set_password('password')
        self.user.save()

        # authenticate the superuser
        self.client.force_login(user=self.user)

        # create some valid authors
        Author.objects.create(name="muhammad", age=20,
                              is_vip=True, user_id=self.user.pk)
        Author.objects.create(name="Ali", age=20,
                              is_vip=False, user_id=self.user.pk)
        Author.objects.create(name="Omar", age=60,
                              is_vip=True, user_id=self.user.pk)
        self.author_info = (Author._meta.app_label, Author._meta.model_name)

        # create some valid publishers
        Publisher.objects.create(name='rock')
        Publisher.objects.create(name='paper')
        Publisher.objects.create(name='scissor')

    def test_list_view(self):
        url = reverse('api_admin:%s_%s_list' % self.author_info)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]['name'], 'muhammad')

    def test_detail_view(self):
        url = reverse('api_admin:%s_%s_detail' %
                      self.author_info, kwargs={'object_id': 1})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['name'], 'muhammad')

    def test_autocomplete_views(self):
        # GET /admin/autocomplete/?term=p&app_label=django_api_admin&model_name=author&field_name=publisher
        url = reverse(
            'api_admin:autocomplete') + '?term=r&app_label=django_api_admin&model_name=author&field_name=publisher'
        response = self.client.get(url)
        data = json.loads(response.data['content'])
        self.assertEqual(int(data['results'][0]['id']), 1)

    def test_performing_custom_actions(self):
        action_dict = {
            'action': 'make_old',
            'selected_ids': [
                1,
                2
            ],
            'select_across': False,
        }

        self.author_info = (Author._meta.app_label, Author._meta.model_name)
        url = reverse('api_admin:%s_%s_perform_action' % self.author_info)
        response = self.client.post(url, data=action_dict)
        self.assertEqual(response.status_code,  200)

    def test_performing_actions(self):
        action_dict = {
            'action': 'delete_selected',
            'selected_ids': [
                1,
                2
            ],
            'select_across': False,
        }
        self.author_info = (Author._meta.app_label, Author._meta.model_name)
        url = reverse('api_admin:%s_%s_perform_action' % self.author_info)
        response = self.client.post(url, data=action_dict)
        self.assertEqual(response.status_code, 200)

    def test_performing_actions_with_select_across(self):
        action_dict = {
            'action': 'delete_selected',
            'selected_ids': [],
            'select_across': True
        }
        url = reverse('api_admin:%s_%s_perform_action' % self.author_info)
        response = self.client.post(url, data=action_dict)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Author.objects.all().exists(), False)

    def test_performing_actions_invalid_request(self):
        action_dict = {
            'action': 'some_weird_action',
            'select_across': 5.0,
        }
        url = reverse('api_admin:%s_%s_perform_action' % self.author_info)
        response = self.client.post(url, data=action_dict)
        self.assertEqual(response.status_code, 400)

    def test_delete_view(self):
        author = Author.objects.create(
            name="test", age=20, is_vip=True, user_id=self.user.pk)
        url = reverse('api_admin:%s_%s_delete' %
                      self.author_info, kwargs={'object_id': author.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Author.objects.filter(pk=author.pk).exists())
        self.assertEqual(
            response.data['detail'], 'The author “test” was deleted successfully.')

    def test_delete_view_bad_to_field(self):
        author = Author.objects.create(
            name="test2", age=20, is_vip=True, user_id=self.user.pk)
        url = reverse('api_admin:%s_%s_delete' % self.author_info, kwargs={
                      'object_id': author.pk}) + '?_to_field=name'
        response = self.client.post(url)
        self.assertEqual(response.status_code, 400)
        self.assertTrue(Author.objects.filter(pk=author.pk).exists())
        self.assertEqual(response.data['detail'],
                         'The field name cannot be referenced.')

    def test_add_view(self):
        url = reverse('api_admin:%s_%s_add' % self.author_info)
        data = {
            'name': 'test4',
            'age': 60,
            'is_vip': True,
            'user': self.user.pk,
        }
        response = self.client.post(url, data=data)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['data']['name'], 'test4')

        author_id = response.data['data']['pk']
        url = reverse('api_admin:%s_%s_history' %
                      self.author_info, kwargs={'object_id': author_id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data[0]['object_repr'], 'test4')

    def test_change_view(self):
        author = Author.objects.create(
            name='hassan', age=60, is_vip=False, user_id=self.user.pk)
        url = reverse('api_admin:%s_%s_change' %
                      self.author_info, kwargs={'object_id': author.pk})
        data = {
            'name': 'muhammad',
            'age': '60',
            'is_vip': True
        }
        response = self.client.patch(url, data=data)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['data']['name'], 'muhammad')

        url = reverse('api_admin:%s_%s_history' % self.author_info,
                      kwargs={'object_id': author.id}) + '?p=1&page_size=1'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.data) == 1)

    def test_pagination_class(self):
        # perform some actions then paginate them
        authors = [
            {
                'name': 'test1',
                'age': '60',
                'is_vip': True,
                'user': self.user.pk
            },
            {
                'name': 'test2',
                'age': '60',
                'is_vip': True,
                'user': self.user.pk
            },
            {
                'name': 'test3',
                'age': '60',
                'is_vip': True,
                'user': self.user.pk
            },
        ]
        for author in authors:
            url = reverse('api_admin:%s_%s_add' % self.author_info)
            self.client.post(url, data=author)

        url = reverse('api_admin:admin_log') + '?page_size=1&p=1'
        response = self.client.get(url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['action_list']), 1)


class InlineModelAdminTestCase(APITestCase, URLPatternsTestCase):
    urlpatterns = [
        path('api_admin/', site.urls),
    ]

    def setUp(self) -> None:
        # create a superuser
        self.user = UserModel.objects.create_superuser(username='admin')
        self.user.set_password('password')
        self.user.save()
        # authenticate the superuser
        self.client.force_login(user=self.user)
        # create some valid publishers
        p1 = Publisher.objects.create(name='Publishing Company')
        p2 = Publisher.objects.create(name='Publishing Agency')
        p3 = Publisher.objects.create(name='Publishing magazine')
        # create some valid authors
        self.a1 = Author.objects.create(
            name="Baumgartner", age=20, is_vip=True, user_id=self.user.pk)
        self.a1.publisher.add(p1)
        self.a2 = Author.objects.create(
            name="Richard Dawkins", age=20, is_vip=False, user_id=self.user.pk)
        self.a2.publisher.add(p2)
        self.a3 = Author.objects.create(
            name="Allen carr", age=60, is_vip=True, user_id=self.user.pk)
        self.a3.publisher.add(p3)
        self.author_info = (Author._meta.app_label, Author._meta.model_name)
        # create some valid Books
        Book.objects.create(title='High performance django', author=self.a1)
        Book.objects.create(title='A devils chaplain', author=self.a2)
        Book.objects.create(title='Easy way to stop smoking', author=self.a3)
        self.book_info = (*self.author_info,
                          Book._meta.app_label, Book._meta.model_name)

    def test_inline_list_view(self):
        url = reverse('api_admin:%s_%s_%s_%s_list' %
                      self.book_info) + '?p=3&page_size=1'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]['title'], 'Easy way to stop smoking')

    def test_inline_detail_view(self):
        url = reverse('api_admin:%s_%s_%s_%s_detail' %
                      self.book_info, kwargs={'object_id': 1})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['title'], 'High performance django')

    def test_inline_add_view(self):
        # valid request
        url = reverse('api_admin:%s_%s_%s_%s_add' % self.book_info)
        response = self.client.post(url, data={
            'title': 'The selfish gene',
            'author': self.a2.pk,
            'credits': 1,
        })
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data['data']['title'], 'The selfish gene')

        # test logging
        url = reverse('api_admin:%s_%s_history' %
                      self.author_info, kwargs={'object_id': self.a2.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data[0]['object_repr'] == 'Richard Dawkins')

        # invalid data
        url = reverse('api_admin:%s_%s_%s_%s_add' % self.book_info)
        response = self.client.post(url, data={
            'author': self.a2.pk
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['title'][0].code, 'required')

    def test_inline_change_view(self):
        # valid change
        url = reverse('api_admin:%s_%s_%s_%s_change' %
                      self.book_info, kwargs={'object_id': 1})
        response = self.client.patch(url, data={
            'title': 'outgrowing god',
            'author': self.a2.pk,
            'credits': 1,
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['data']['title'], 'outgrowing god')
        self.assertEqual(response.data['data']['author'], self.a2.pk)

        # change being logged
        url = reverse('api_admin:%s_%s_history' %
                      self.author_info, kwargs={'object_id': self.a2.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        change_message = json.loads(response.data[0]['change_message'])
        self.assertTrue(change_message[0]['changed']
                        ['object'] == 'outgrowing god')

        # invalid change
        url = reverse('api_admin:%s_%s_%s_%s_change' %
                      self.book_info, kwargs={'object_id': 1})
        response = self.client.put(url, data={
            'author': self.a2.pk
        })
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['title'][0].code, 'required')

    def test_inline_delete_view(self):
        url = reverse('api_admin:%s_%s_%s_%s_delete' %
                      self.book_info, kwargs={'object_id': 3})
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 200)
        try:
            Book.objects.get(id=3)
        except Book.DoesNotExist:
            assert True

    def test_inline_form_fields(self):
        url = reverse('api_admin:%s_%s_%s_%s_add' % self.book_info)
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['fields']), 3)

        url = reverse('api_admin:%s_%s_%s_%s_change' %
                      self.book_info, kwargs={'object_id': 1})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data['fields']), 3)
        self.assertEqual(
            response.data['fields'][0]['attrs']['current_value'], 'High performance django')
