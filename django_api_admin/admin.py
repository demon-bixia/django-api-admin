from .models import Author
from .sites import APIAdminSite, site
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

site.register(Author)
site.register(User, UserAdmin)