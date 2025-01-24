from django.utils.translation import gettext as _

from rest_framework import status
from rest_framework.response import Response

from django_api_admin.decorators import action


@action(description='make all authors old')
def make_old(model_admin, request, queryset):
    queryset.update(age=60)
    return Response({'detail': 'All select authors are old now'}, status=status.HTTP_200_OK)


@action(description='make all authors young')
def make_young(model_admin, request, queryset):
    queryset.update(age=1)
    return Response({'detail': 'All select authors are young now'}, status=status.HTTP_200_OK)
