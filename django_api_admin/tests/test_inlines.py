"""
inline admins views.
"""
from django.contrib.auth import get_user_model
from django.urls import path, reverse
from rest_framework.test import (APITestCase,
                                 URLPatternsTestCase)

from django_api_admin.models import Author, Book, Publisher
from django_api_admin.sites import site
from django_api_admin.utils.force_login import force_login


UserModel = get_user_model()


class InlineModelAdminTestCase(APITestCase, URLPatternsTestCase):
    urlpatterns = [
        path('api_admin/', site.urls),
    ]

    def setUp(self) -> None:
        # create and authenticate a superuser
        self.user = UserModel.objects.create_superuser(username='admin')
        self.user.set_password('password')
        self.user.save()
        force_login(self.client, self.user)

        # create some valid authors
        self.a1 = Author.objects.create(
            name="Baumgartner", age=20, is_vip=True, user_id=self.user.pk)
        self.a2 = Author.objects.create(
            name="Richard Dawkins", age=20, is_vip=False, user_id=self.user.pk)
        self.a3 = Author.objects.create(
            name="Allen carr", age=60, is_vip=True, user_id=self.user.pk)
        self.author_info = (Author._meta.app_label, Author._meta.model_name)

        # create a valid publisher
        Publisher.objects.create(name='rock')

        # create some valid Books
        self.a1_b1 = Book.objects.create(
            title='High performance django', author=self.a1)
        self.a1_b2 = Book.objects.create(
            title='Clean architecture', author=self.a1)
        self.a1_b3 = Book.objects.create(title='Pro git', author=self.a1)
        self.a2_b1 = Book.objects.create(
            title='A devils chaplain', author=self.a2)
        self.a3_b1 = Book.objects.create(
            title='Easy way to stop smoking', author=self.a3)
        self.book_info = (*self.author_info,
                          Book._meta.app_label, Book._meta.model_name)

    def test_inline_bulk_additions(self):
        url = reverse('api_admin:%s_%s_add' % self.author_info)
        data = {
            "data": {
                "name": "Sergei Brin",
                "age": 60,
                "user": self.user.pk,
                "is_vip": False,
                'publisher': [1]
            },
            "create_inlines": {
                "books": [
                    {
                        "title": "The freedom model",
                        "credits": [self.a1.pk]
                    },
                    {
                        "title": "API security oauth2 and beyond",
                        "credits": [self.a1.pk]
                    },
                    {
                        "title": "OpenId connect in action",
                        "credits": [self.a1.pk]
                    }

                ]
            }
        }
        response = self.client.post(url, data=data, format="json")
        self.assertEqual(response.status_code, 201)
        self.assertIsNotNone(response.data.get('created_inlines'))
        self.assertEqual(len(response.data.get('created_inlines')), 3)

    def test_inline_bulk_updates(self):
        url = reverse('api_admin:%s_%s_change' %
                      self.author_info, kwargs={'object_id': self.a1.pk})
        data = {
            "data": {
                "name": "René Descartes",
                "age": 60,
                "user": self.user.pk,
                "is_vip": True,
                'publisher': [1]
            },
            "update_inlines": {
                "books": [
                    {
                        "pk": self.a1_b1.pk,
                        "title": "The book of nine secrets",
                        "credits": [self.a2.pk]
                    },
                    {
                        "pk": self.a1_b2.pk,
                        "title": "purple thunder lightning technique",
                        "credits": [self.a2.pk]
                    }
                ]
            },
            "delete_inlines": {
                "books": [
                    {
                        "pk": self.a1_b3.pk
                    }
                ]
            }
        }
        response = self.client.put(url, data=data, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(response.data.get('updated_inlines'))
        self.assertEqual(len(response.data.get('updated_inlines')), 2)
        self.assertEqual(response.data.get("updated_inlines")[
                         0]['title'], "The book of nine secrets")
        self.assertIsNotNone(response.data.get('deleted_inlines'))
        self.assertEqual(len(response.data.get('deleted_inlines')), 1)
        self.assertEqual(response.data.get(
            "deleted_inlines")[0]['title'], "Pro git")

    def test_updating_unrelated_inlines(self):
        url = reverse('api_admin:%s_%s_change' %
                      self.author_info, kwargs={'object_id': self.a1.pk})
        data = {
            "data": {
                "name": "René Descartes",
                "age": 60,
                "user": self.user.pk,
                "is_vip": True
            },
            "update_inlines": {
                "books": [
                    {
                        "pk": self.a1_b1.pk,
                        "title": "The book of nine secrets",
                        "credits": [self.a2.pk]
                    },

                    {
                        "pk": self.a3_b1.pk,
                        "title": "The book of nine secrets",
                        "credits": [self.a2.pk]
                    }
                ],
            },
            "delete_inlines":  {
                "books": [
                    {
                        "pk": self.a3_b1.pk
                    }
                ]
            }
        }
        response = self.client.put(url, data=data, format="json")
        self.assertEqual(response.status_code, 400)
