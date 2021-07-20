from django.urls import path

from django_api_admin.sites import APIAdminSite
from . import views as custom_api_views


class CustomAPIAdminSite(APIAdminSite):
    include_root_view = False
    include_view_on_site_view = False
    include_final_catch_all_view = True

    def hello_world_view(self, request):
        return custom_api_views.HelloWorldView.as_view()(request)

    def get_urls(self):
        urlpatterns = super(CustomAPIAdminSite, self).get_urls()
        urlpatterns.insert(len(urlpatterns) - 1, path('hello_world/', self.hello_world_view, name='hello'), )
        return urlpatterns


site = CustomAPIAdminSite('custom_api_admin')
