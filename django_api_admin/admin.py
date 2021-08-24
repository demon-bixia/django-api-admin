"""These admins are used in tests.py to test django_api_admin."""
from django.contrib import admin

from .models import Author, Publisher, Book
from .options import APIModelAdmin, TabularInlineAPI
from .sites import site


class APIBookInline(TabularInlineAPI):
    model = Book


@admin.register(Publisher, site=site)
class PublisherAPIAdmin(APIModelAdmin):
    search_fields = ('name',)


# register in api_admin_site
@admin.register(Author, site=site)
class AuthorAPIAdmin(APIModelAdmin):
    list_display = ('name', 'age', 'user', 'is_old_enough', 'gender')
    list_filter = ('is_vip', 'age')
    list_per_page = 2
    search_fields = ('name',)
    raw_id_fields = ('publisher',)
    ordering = ('-age',)
    fieldsets = (
        ('Information', {'fields': (('name', 'age'), 'is_vip', 'user', 'gender')}),
    )
    date_hierarchy = 'date_joined'
    exclude = ('gender',)
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
    list_display = ('name', 'age', 'is_a_vip', 'user', 'gender')
    list_filter = ('is_vip', 'age')
    list_per_page = 4
    raw_id_fields = ('publisher',)
    autocomplete_fields = ('publisher',)
    search_fields = ('name',)
    ordering = ('-age',)
    fieldsets = (
        ('Information', {'fields': (('name', 'age'), 'is_vip', 'user')}),
    )
    # a list of field names to exclude from the add/change form.
    exclude = ('gender',)
    date_hierarchy = 'date_joined'

    inlines = [BookInline]

    @admin.display(description='is this author a vip')
    def is_a_vip(self, obj):
        return obj.is_vip


admin.site.register(Author, AuthorAdmin)
admin.site.register(Publisher, PublisherAdmin)
