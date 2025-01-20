from django.utils.translation import gettext_lazy as _


def get_inline_by_field_name(request, model_admin, inline_name):
    """
    extract the InlineModelAdmin from the ModelAdmin based on the name of the InlineModelAdmin
    """
    inline_admin = None
    for inline_instance in model_admin.get_inline_instances(request):
        if inline_instance.model._meta.verbose_name_plural == inline_name:
            inline_admin = inline_instance
    return inline_admin
