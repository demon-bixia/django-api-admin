"""
urlpatterns used for testing not included in production.
"""

from django.contrib import admin
from django.urls import path
from django_api_admin.admin import site
from django_api_admin.views import fields_test_views

urlpatterns = [
    # both the api admin and the default admin
    path('admin/', admin.site.urls),
    path('api_admin/', site.urls),

    # test your form fields.
    path('api_admin/test/<str:test_name>/', fields_test_views.TestView.as_view()),
    path('api_admin/test/test_detail/<pk>/',
         fields_test_views.TestDetailView.as_view(), name="test-detail"),
    path('api_admin/test/test_detail/<pk>/<format>/',
         fields_test_views.TestDetailView.as_view(), name="test-detail")
]
