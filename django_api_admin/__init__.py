from django.utils.module_loading import autodiscover_modules

from django_api_admin.decorators import action, display, register
from django_api_admin.filters import (
    AllValuesFieldListFilter,
    BooleanFieldListFilter,
    ChoicesFieldListFilter,
    DateFieldListFilter,
    EmptyFieldListFilter,
    FieldListFilter,
    ListFilter,
    RelatedFieldListFilter,
    RelatedOnlyFieldListFilter,
    SimpleListFilter,
)
from django_api_admin.constants.vars import HORIZONTAL, VERTICAL
from django_api_admin.admins.model_admin import APIModelAdmin
from django_api_admin.admins.inline_admin import StackedInlineAPI, TabularInlineAPI
from django_api_admin.sites import APIAdminSite, site

__all__ = [
    "action",
    "display",
    "register",
    "APIModelAdmin",
    "HORIZONTAL",
    "VERTICAL",
    "StackedInlineAPI",
    "TabularInlineAPI",
    "APIAdminSite",
    "site",
    "ListFilter",
    "SimpleListFilter",
    "FieldListFilter",
    "BooleanFieldListFilter",
    "RelatedFieldListFilter",
    "ChoicesFieldListFilter",
    "DateFieldListFilter",
    "AllValuesFieldListFilter",
    "EmptyFieldListFilter",
    "RelatedOnlyFieldListFilter",
    "autodiscover",
]


def autodiscover():
    autodiscover_modules("admin", register_to=site)
