"""
Test admins are used in tests.py to test django_api_admin.
not included in the production branch
"""
from django.contrib import admin
from django.urls import path

from test_django_api_admin import views as custom_api_views
from test_django_api_admin.models import Author, Publisher, Book, GuestEntry
from test_django_api_admin.actions import make_old, make_young
from django_api_admin.sites import APIAdminSite
from django_api_admin.admins.inline_admin import TabularInlineAPI
from django_api_admin.admins.model_admin import APIModelAdmin
from django_api_admin.decorators import register, display


class CustomAPIAdminSite(APIAdminSite):
    include_root_view = False
    include_view_on_site_view = True

    def hello_world_view(self, request):
        return custom_api_views.HelloWorldView.as_view()(request)

    def get_urls(self):
        urlpatterns = super(CustomAPIAdminSite, self).get_urls()
        urlpatterns.append(
            path('hello_world/', self.hello_world_view, name='hello'))
        return urlpatterns


site = CustomAPIAdminSite(name='api_admin', include_auth=True)


class APIBookInline(TabularInlineAPI):
    model = Book


@register(Publisher, site=site)
class PublisherAPIAdmin(APIModelAdmin):
    search_fields = ('name',)


# register in api_admin_site
@register(Author, site=site)
class AuthorAPIAdmin(APIModelAdmin):
    list_display = ('name', 'age', 'user', 'is_old_enough',
                    'title', 'gender',)
    exclude = ('gender',)
    list_display_links = ('name',)
    list_filter = ('is_vip', 'age')
    list_editable = ('title',)
    list_per_page = 6
    empty_value_display = '-'

    actions = (make_old, make_young,)
    actions_selection_counter = True

    date_hierarchy = 'date_joined'
    search_fields = ('name', 'publisher__name',)
    ordering = ('-age',)

    raw_id_fields = ('publisher',)
    # fieldsets = (
    # ('Personal Information', {
    #  'fields': (('name', 'age'),  'user', 'is_vip', 'gender', 'publisher')}),
    # )
    inlines = [APIBookInline, ]

    @display(description='is this author old enough')
    def is_old_enough(self, obj):
        return obj.age > 10


# register in default admin site
class BookInline(admin.TabularInline):
    model = Book


class PublisherAdmin(admin.ModelAdmin):
    search_fields = ('name',)


class AuthorAdmin(admin.ModelAdmin):
    list_display = ('name', 'age', 'is_a_vip',
                    'user', 'is_old_enough', 'title', 'gender', )
    list_filter = ('is_vip', 'age')
    list_editable = ('age',)
    list_per_page = 6
    empty_value_display = '-'
    search_fields = ('name',)

    # filter_horizontal = ('publisher')

    actions = (make_old, make_young,)

    raw_id_fields = ('publisher', )
    autocomplete_fields = ('publisher',)
    date_hierarchy = 'date_joined'

    ordering = ('-age',)
    fieldsets = (
        ('Information', {
         'fields': (('name', 'age'), 'is_vip', 'user', 'publisher')}),
    )
    # a list of field names to exclude from the add/change form.
    exclude = ('gender',)

    filter_horizontal = ('credits',)

    inlines = [BookInline]

    @admin.display(description='is this author a vip')
    def is_a_vip(self, obj):
        return obj.is_vip

    @admin.display(description='is this author old enough')
    def is_old_enough(self, obj):
        return obj.age > 10


admin.site.register(Author, AuthorAdmin)
admin.site.register(Publisher, PublisherAdmin)
admin.site.register(GuestEntry)
