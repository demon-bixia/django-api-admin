from django.utils.translation import gettext_lazy as _
from django.forms.models import _get_foreign_key

from django_api_admin.utils.get_form_config import get_form_config
from django_api_admin.utils.get_form_fields import get_form_fields
from django_api_admin.utils.get_related_name import get_related_name
from django_api_admin.utils.remove_field import remove_field


def get_inlines(request, model_admin, obj=None):
    """
    generates the data used to represent inline admins.
    """
    inlines = []

    for inline_admin in model_admin.get_inline_instances(request):
        serializer_class = inline_admin.get_serializer_class()
        fk = _get_foreign_key(inline_admin.parent_model,
                              inline_admin.model, fk_name=inline_admin.fk_name)

        inline = {
            'name': inline_admin.model._meta.verbose_name_plural,
            'object_name': inline_admin.model._meta.verbose_name,
            'admin_name':  inline_admin.parent_model._meta.app_label + '_' + inline_admin.parent_model._meta.model_name + '_' + inline_admin.model._meta.model_name,
            'config': get_form_config(inline_admin),
            'fk_name': fk.name
        }

        if obj:
            # in case of change view create a fieldset for every related instance to our parent model
            fk_field = getattr(obj, get_related_name(fk), None)
            related_instances = fk_field.all()
            fieldsets = []
            for instance in related_instances:
                serializer = serializer_class(instance=instance)
                fields = get_form_fields(serializer, change=True)
                remove_field(fields, fk.name)
                fieldsets.append({'pk': instance.pk, 'fields': fields})
            inline['fieldsets'] = fieldsets
        else:
            # in case of add view simply add a list of fields.
            serializer = serializer_class()
            fields = get_form_fields(serializer)
            # remove the foreign key field used to tie the inline_model admin with the model_admin.
            remove_field(fields, fk.name)
            inline['fields'] = fields

        # add inline to inlines list
        inlines.append(inline)

    return inlines
