from django.contrib import admin

from .models import Author
from .options import APIModelAdmin
from .sites import site


# register in api_admin_site
class AuthorAPIAdmin(APIModelAdmin):
    list_display = ['name', 'is_old_enough']
    list_filter = ['is_vip', 'age']
    list_per_page = 2

    @admin.display(description='is this author old enough')
    def is_old_enough(self, obj):
        return obj.age > 10


site.register(Author, AuthorAPIAdmin)


# register in default admin site
class AuthorAdmin(admin.ModelAdmin):
    list_display = ('name', 'age', 'is_a_vip')
    list_filter = ('is_vip', 'age')
    list_per_page = 4
    search_fields = ('name',)

    @admin.display(description='is this author a vip')
    def is_a_vip(self, obj):
        return obj.is_vip


admin.site.register(Author, AuthorAdmin)
