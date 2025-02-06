from django.db.models import Model
from django.utils.translation import gettext_lazy as _

from rest_framework.utils import humanize_datetime

from django_api_admin.constants.field_attributes import field_attributes


def get_field_attributes(name, field, change, serializer):
    """
    extracts attributes from the serializer fields that are used to create forms
    on the frontend.
    """
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
