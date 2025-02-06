from django.utils.translation import gettext_lazy as _

from rest_framework import serializers


def validate_inline_field_names(request, inlines,  model_admin):
    """
    validates a list of field names to make sure each name is a valid inline in the mode admin.
    """
    # generate a list containing names of the fields to add and update model admins.
    inline_admin_field_names = []
    for inline_admin in model_admin.get_inline_instances(request):
        inline_admin_field_names.append(
            inline_admin.model._meta.verbose_name_plural)

    # make sure the user used the correct inline names.
    name_errors = {}
    for inline_name in inlines.keys():
        if inline_name not in inline_admin_field_names:
            name_errors[inline_name] = [
                _("there is no inline admin with this name in model admin")]

    # raise inline doesn't exist error
    if len(name_errors) > 0:
        raise serializers.ValidationError({"inline_errors": name_errors})
