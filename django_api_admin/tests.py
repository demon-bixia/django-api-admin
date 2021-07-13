from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase, URLPatternsTestCase, APIRequestFactory, force_authenticate
from django_api_admin.views import LoginView, LogoutView, PasswordChangeView, IndexView
from django.urls import path
from django_api_admin.sites import APIAdminSite, site
from django_api_admin.models import Author
from rest_framework.renderers import JSONRenderer
from django.apps import apps

UserModel = get_user_model()
renderer = JSONRenderer()


class AuthenticationTestCase(APITestCase, URLPatternsTestCase):
    urlpatterns = [
        path('admin/', site.urls),
    ]

    def test_non_staff_user_login(self):
        user = UserModel.objects.create(username='test')
        user.set_password('password')
        user.save()

        url = reverse('admin:login')
        response = self.client.post(url, {'username': user.username, 'password': 'password'})
        self.assertEqual(response.status_code, 403)

    def test_staff_user_login(self):
        user = UserModel.objects.create_superuser(username='admin')
        user.set_password('password')
        user.save()

        url = reverse('admin:login')
        response = self.client.post(url, {'username': user.username, 'password': 'password'})
        self.assertEqual(response.status_code, 200)

    def test_logout_user_logged_in(self):
        user = UserModel.objects.create_superuser(username='admin')
        user.set_password('password')
        user.save()

        self.client.force_login(user=user)
        url = reverse('admin:logout')
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.data.get('message', None))

    # todo make it work with status code 200
    def test_logout_user_not_logged_in(self):
        user = UserModel.objects.create_superuser(username='admin')
        user.set_password('password')
        user.save()

        url = reverse('admin:logout')
        response = self.client.post(url)
        self.assertEqual(response.status_code, 302)
        # self.assertIsNotNone(response.get('message', None))

    def test_password_change(self):
        user = UserModel.objects.create_superuser(username='test')
        user.set_password('password')
        user.save()

        url = reverse('admin:password_change')
        self.client.force_login(user=user)
        response = self.client.post(url, {'old_password': 'password', 'new_password1': 'new_password',
                                          'new_password2': 'new_password'})
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.data.get('message', None))

    def test_password_change_password_mismatch(self):
        user = UserModel.objects.create_superuser(username='test')
        user.set_password('password')
        user.save()

        url = reverse('admin:password_change')
        self.client.force_login(user=user)
        response = self.client.post(url, {'old_password': 'password', 'new_password1': 'something',
                                          'new_password2': 'something else'})
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.data['non_field_errors'][0].code, 'password_mismatch')


site.register(Author)


class APIAdminSiteTestCase(APITestCase, URLPatternsTestCase):
    urlpatterns = [
        path('admin/', site.urls),
    ]

    def setUp(self) -> None:
        self.factory = APIRequestFactory()

        # create a superuser
        self.user = UserModel.objects.create_superuser(username='admin')
        self.user.set_password('password')
        self.user.save()

        # authenticate the superuser
        self.client.force_login(self.user)

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
        url = reverse('admin:index')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_app_index_view(self):
        # test if the app_index view works
        app_label = Author._meta.app_label
        url = reverse('admin:app_list', kwargs={'app_label': app_label})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)