from django.db.models import Model
from django.forms import model_to_dict
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.fields import _UnvalidatedField
from rest_framework.utils import humanize_datetime
from rest_framework.utils.field_mapping import get_field_kwargs

from .serializer_field_attributes import field_attributes


class ModelDiffHelper(object):
    def __init__(self, initial):
        self.__initial = self._dict(initial)
        self._new_object = None

    def set_changed_model(self, new_object):
        data = self._dict(new_object)
        if self._new_object is not None:
            self.__initial = data
        self._new_object = data
        return self

    @property
    def diff(self):
        if not self._new_object:
            return {}
        d1 = self.__initial
        d2 = self._new_object
        diffs = [(k, (v, d2[k])) for k, v in d1.items() if v != d2[k]]
        return dict(diffs)

    @property
    def has_changed(self):
        return bool(self.diff)

    @property
    def changed_fields(self):
        return list(self.diff.keys())

    def get_field_diff(self, field_name):
        """
        Returns a diff for field if it's changed and None otherwise.
        """
        return self.diff.get(field_name, None)

    def _dict(self, model):
        return model_to_dict(model, fields=[field.name for field in
                                            model._meta.fields])


def get_field_attributes(name, field, change, serializer):
    # create a field dict with name of the field, and it's type
    # (i.e 'name': 'username', 'type': 'CharField', 'attrs': {'max_length': 50, ...})

    form_field = {'type': type(field).__name__, 'name': name, 'attrs': {}}

    for attr_name in field_attributes[form_field['type']]:
        attr = getattr(field, attr_name, None)
        # if the attribute is an empty field (not set attribute) use null
        if attr_name == 'default' and getattr(attr, "__name__", None) == 'empty':
            value = False if type(
                field).__name__ == "BooleanField" else None
        # if the attribute is a callable then call it and pass field to it
        elif callable(attr):
            value = attr(field)

        # the input_format attribute should be a humanized list of date or datetime formats or
        # default to iso-8601
        elif attr_name == 'input_formats':
            if type(field).__name__ == "DateField":
                value = humanize_datetime.date_formats(attr).split(
                    ", ") if attr else humanize_datetime.date_formats(['iso-8601']).split(", ")
            elif type(field).__name__ == "DateTimeField":
                value = humanize_datetime.datetime_formats(attr).split(
                    ", ") if attr else humanize_datetime.datetime_formats(['iso-8601']).split(", ")
            elif type(field).__name__ == "TimeField":
                value = humanize_datetime.time_formats(attr).split(
                    ", ") if attr else humanize_datetime.time_formats(['iso-8601']).split(", ")
        else:
            # if it's a primitive value or None just use it
            value = attr

        form_field['attrs'][attr_name] = value

    if change:
        current_value = serializer.data.get(name)

        if isinstance(current_value, Model):
            current_value = current_value.pk

        form_field['attrs']['current_value'] = current_value

    return form_field


def get_form_fields(serializer, change=False):
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
