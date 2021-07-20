from django.contrib.auth import get_user_model
from django.urls import path, reverse, NoReverseMatch
from rest_framework.test import APITestCase, URLPatternsTestCase

from .admin import site
from .models import Person

site.register(Person)
UserModel = get_user_model()


class CustomAPITestCase(APITestCase, URLPatternsTestCase):
    urlpatterns = [
        path('custom_admin/', site.urls),
    ]

    def setUp(self) -> None:
        # create a superuser
        self.user = UserModel.objects.create_superuser(username='admin')
        self.user.set_password('password')
        self.user.save()

        # authenticate the superuser
        self.client.force_login(self.user)

    def test_site_name(self):
        self.assertEqual(site.name, 'custom_api_admin')

    def test_index_view(self):
        # test if the index view works in a custom admin site
        url = reverse(f'{site.name}:index')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_app_index_view(self):
        # test if the app index view works in a custom admin site
        url = reverse(f'{site.name}:app_list', kwargs={'app_label': Person._meta.app_label})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_root_view_disabled(self):
        try:
            url = reverse(f'{site.name}:api-root')
            assert False
        except NoReverseMatch:
            assert True

    def test_final_catch_all_view(self):
        url = '/custom_admin/index'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 301)

    def test_custom_url_view(self):
        url = reverse(f'{site.name}:hello')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data['message'], 'hello world')
