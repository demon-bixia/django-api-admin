from django.contrib import admin
from django.urls import path
from django_api_admin.admin import site
from django_api_admin import test_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api_admin/', site.urls),
    path('api_admin/test/<str:test_name>/', test_views.TestView.as_view()),
    path('api_admin/test/test_detail/<pk>/',
         test_views.TestDetailView.as_view(), name="test-detail"),
    path('api_admin/test/test_detail/<pk>/<format>/',
         test_views.TestDetailView.as_view(), name="test-detail")
]
