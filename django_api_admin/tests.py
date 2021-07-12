from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase, URLPatternsTestCase
from django_api_admin.views import LoginView, LogoutView
from django.urls import path

UserModel = get_user_model()


class AuthenticationTestCase(APITestCase, URLPatternsTestCase):
    urlpatterns = [
        path('apiadmin/login', LoginView.as_view(), name='login'),
        path('apiadmin/logout', LogoutView.as_view(), name='logout')
    ]

    def test_non_staff_user_login(self):
        user = UserModel.objects.create(username='test')
        user.set_password('password')
        user.save()

        url = reverse('login')
        response = self.client.post(url, {'username': user.username, 'password': 'password'})
        self.assertEqual(response.status_code, 403)

    def test_staff_user_login(self):
        user = UserModel.objects.create_superuser(username='admin')
        user.set_password('password')
        user.save()

        url = reverse('login')
        response = self.client.post(url, {'username': user.username, 'password': 'password'})
        self.assertEqual(response.status_code, 200)

    def test_logout_user_logged_in(self):
        user = UserModel.objects.create_superuser(username='admin')
        user.set_password('password')
        user.save()

        self.client.force_login(user=user)
        url = reverse('logout')
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.data.get('message', None))

    def test_logout_user_not_logged_in(self):
        user = UserModel.objects.create_superuser(username='admin')
        user.set_password('password')
        user.save()

        url = reverse('logout')
        response = self.client.post(url)
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.data.get('message', None))

