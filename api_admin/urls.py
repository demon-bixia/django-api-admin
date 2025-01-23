"""
urlpatterns used for testing not included in production.
"""

from django.contrib import admin
from django.urls import path
from django_api_admin.admin import site
from django_api_admin.views import e2e

urlpatterns = [
    # both the api admin and the default admin
    path('admin/', admin.site.urls),
    path('api_admin/', site.urls),

    # test your form fields.
    path('api_admin/test/<str:test_name>/', e2e.TestView.as_view()),
    path('api_admin/test/test_detail/<pk>/',
         e2e.TestDetailView.as_view(), name="test-detail"),
    path('api_admin/test/test_detail/<pk>/<format>/',
         e2e.TestDetailView.as_view(), name="test-detail")
]
