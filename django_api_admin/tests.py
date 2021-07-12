from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase, URLPatternsTestCase
from django_api_admin.views import LoginView
from django.urls import path
from django.contrib.auth.models import UserManager

UserModel = get_user_model()


class AuthenticationTestCase(APITestCase, URLPatternsTestCase):
    urlpatterns = [
        path('apiadmin/login', LoginView.as_view(), name='login')
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
