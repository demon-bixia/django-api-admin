from django.contrib import admin
from django.urls import path
from test_django_api_admin.admin import site
from test_django_api_admin import views

urlpatterns = [
    # both the api admin and the default admin
    path('admin/', admin.site.urls),
    path('api_admin/', site.urls),
    # test your form fields.
    # path('api_admin/field_tests/<str:test_name>/', views.TestView.as_view()),
    # path('api_admin/field_tests/test_detail/<pk>/',
    #     views.TestDetailView.as_view(), name="test-detail"),
    # path('api_admin/field_tests/test_detail/<pk>/<format>/',
    #     views.TestDetailView.as_view(), name="test-detail")
]
