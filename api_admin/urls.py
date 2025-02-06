from django.contrib import admin
from django.urls import path

from test_django_api_admin import views
from test_django_api_admin.admin import site

urlpatterns = [
    # both the api admin and the default admin
    path('admin/', admin.site.urls),
    path('api_admin/', site.urls),
    path('api/author/<int:pk>/',
         views.AuthorDetailView.as_view(), name="author-detail"),
    # test your form fields.
    # path('api_admin/field_tests/<str:test_name>/', views.TestView.as_view()),
]
