"""
authentication tests
"""
from django.contrib.auth import get_user_model
from django.urls import path, reverse

from rest_framework.parsers import JSONParser
from rest_framework.renderers import JSONRenderer
from rest_framework.test import (APITestCase,
                                 URLPatternsTestCase)

from django_api_admin.sites import site

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

