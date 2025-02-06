from django.utils.translation import gettext_lazy as _


def remove_field(fields, name):
    """
    removes a field from a list of fields generated by
    get_form_fields
    """
    for idx, field in enumerate(fields):
        if field['name'] == name:
            del fields[idx]
    return fields
