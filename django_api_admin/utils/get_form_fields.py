from django.utils.translation import gettext_lazy as _

from rest_framework import serializers
from rest_framework.fields import _UnvalidatedField
from rest_framework.utils.field_mapping import get_field_kwargs

from django_api_admin.utils.get_field_attributes import get_field_attributes


def get_form_fields(serializer, change=False):
    """
    given a serializer this function picks which fields should be
    used to create forms.
    """
    form_fields = list()

    # loop all serializer fields
    for name, field in serializer.fields.items():
        # don't create a form field for the pk field
        if name != 'pk' and not field.read_only and type(field).__name__ not in ['HiddenField',
                                                                                 'ReadOnlyField',
                                                                                 'SerializerMethodField',
                                                                                 'HyperlinkedIdentityField']:
            # if it's a model field then get attributes for the child field not the model field it self
            if type(field) == serializers.ModelField:
                field_kwargs = get_field_kwargs(
                    field.model_field.verbose_name, field.model_field)
                field_kwargs.pop('model_field')
                field = serializers.ModelSerializer.serializer_field_mapping[field.model_field.__class__](
                    **field_kwargs)

            form_field = get_field_attributes(
                name, field, change, serializer)

            # include child fields
            if type(field) in [serializers.ListField, serializers.DictField, serializers.HStoreField] and type(form_field['attrs']['child']) != _UnvalidatedField:
                form_field['attrs']['child'] = get_field_attributes(field.child.field_name, field.child,
                                                                    change,
                                                                    serializer)
            # if no child set child to null
            elif type(form_field['attrs'].get('child', None)) is _UnvalidatedField:
                form_field['attrs']['child'] = None

            form_fields.append(form_field)

    return form_fields
