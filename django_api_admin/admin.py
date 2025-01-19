"""
Test admins are used in tests.py to test django_api_admin.
not included in the production branch
"""
from django.contrib import admin

from .models import Author, Publisher, Book, GuestEntry
from .options import APIModelAdmin, TabularInlineAPI
from .sites import site
from .actions import make_old, make_young


class APIBookInline(TabularInlineAPI):
    model = Book


@admin.register(Publisher, site=site)
class PublisherAPIAdmin(APIModelAdmin):
    search_fields = ('name',)


# register in api_admin_site
@admin.register(Author, site=site)
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
    fieldsets = (
        ('Personal Information', {
         'fields': (('name', 'age'),  'user', 'is_vip', 'gender', 'publisher')}),
    )
    inlines = [APIBookInline, ]

    @admin.display(description='is this author old enough')
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
