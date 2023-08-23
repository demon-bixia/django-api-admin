"""
Shared miscellaneous functions.
"""
from django.db.models import Model
from django.utils.translation import gettext_lazy as _
from django.forms.models import _get_foreign_key

from rest_framework import serializers
from rest_framework.fields import _UnvalidatedField
from rest_framework.utils import humanize_datetime
from rest_framework.utils.field_mapping import get_field_kwargs

from django_api_admin.field_attributes import field_attributes


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


def get_inlines(request, model_admin, obj=None):
    """
    generates the data used to represent inline admins.
    """
    inlines = []

    for inline_admin in model_admin.get_inline_instances(request, obj=None):
        serializer_class = inline_admin.get_serializer_class(request)
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


def remove_field(fields, name):
    """
    removes a field from a list of fields generated by
    get_form_fields
    """
    for idx, field in enumerate(fields):
        if field['name'] == name:
            del fields[idx]
    return fields


def get_form_config(model_admin):
    """
    get model admin form attributes.
    """
    config = {}
    for option_name in model_admin.form_options:
        config[option_name] = getattr(
            model_admin, option_name, None
        )
    return config


def validate_inline_field_names(request, inlines,  model_admin):
    """
    validates a list of field names to make sure each name is a valid inline in the mode admin.
    """
    # generate a list containing names of the fields to add and update model admins.
    inline_admin_field_names = []
    for inline_admin in model_admin.get_inline_instances(request, obj=None):
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


def get_inline_by_field_name(request, model_admin, inline_name):
    """
    extract the InlineModelAdmin from the ModelAdmin based on the name of the InlineModelAdmin
    """
    inline_admin = None
    for inline_instance in model_admin.get_inline_instances(request, obj=None):
        if inline_instance.model._meta.verbose_name_plural == inline_name:
            inline_admin = inline_instance
    return inline_admin


def validate_bulk_edits(request, model_admin, obj, operation="create_inlines"):
    """
    validates datasets used to create ...
    """
    # validate the names of the fields
    validate_inline_field_names(
        request, request.data.get(operation), model_admin)

    # validate the inline data
    valid_serializers = []
    serializer_errors = []
    for inline_name, inline_datasets in request.data.get(operation).items():
        # extract the InlineModelAdmin from the ModelAdmin based on the name of the InlineModelAdmin
        inline_admin = get_inline_by_field_name(
            request, model_admin, inline_name)
        # get the fk used to create the inline relationship as well as the serializer class
        fk = _get_foreign_key(inline_admin.parent_model,
                              inline_admin.model, fk_name=inline_admin.fk_name)
        inline_serializer_class = inline_admin.get_serializer_class(request)

        # in the case of change view make sure all provided instances are related to the model
        # and preload all instances for updating
        fk_field = None
        instances = None
        if operation == "update_inlines":
            fk_field = getattr(obj, get_related_name(fk), None)
            primary_keys = [dataset['pk'] for dataset in inline_datasets]
            instances = fk_field.filter(pk__in=primary_keys)

            # if no instances are matched then raise an error
            if instances.count() == 0:
                raise serializers.ValidationError(
                    {"error": "you did't include any inline that is related to this model"})
            # make sure all instances are related to the model_admin model
            if instances.count() != len(primary_keys):
                raise serializers.ValidationError(
                    {"error": "you can't update an inline that is not related to this model"})

        # in the case of deleting inlines make sure all provided primary keys are related to the model
        if operation == 'delete_inlines':
            deleted_instances = []
            # get the list of all primary keys included in the datasets
            primary_keys = [
                inline_dataset['pk'] for inline_dataset in inline_datasets]
            # get the instances to be deleted
            instances = inline_admin.model.objects.filter(
                pk__in=primary_keys)
            # if no instances are matched then raise an error
            if instances.count() == 0:
                raise serializers.ValidationError(
                    {"error": "you did't include any inline that is related to this model"})
            # make sure all instances are related to the model_admin model
            if instances.count() != len(primary_keys):
                raise serializers.ValidationError(
                    {"error": "you can't delete an inline that is not related to this model"})

            # serialize the instance and add to the the array
            serializer_class = inline_admin.get_serializer_class(request)
            for instance in instances:
                serializer = serializer_class(instance)
                deleted_instances.append(serializer.data)

            return instances, deleted_instances

        # loop all data sets and validate using serializer class
        for idx, inline_dataset in enumerate(inline_datasets):
            data = inline_dataset
            # add the object pk to the fk field to create the relationship this requires the new_object to be created
            data[fk.name] = obj.pk

            # create the serializer instance
            inline_serializer = None
            if operation == "update_inlines":
                # in the case of change view create a serializer with the related instance and data
                instance = instances[idx]
                inline_serializer = inline_serializer_class(
                    instance, data=data, partial=True)
            else:
                # in the case of add view just create a serializer with the data
                inline_serializer = inline_serializer_class(data=data)

            if inline_serializer.is_valid():
                valid_serializers.append(inline_serializer)
            else:
                serializer_errors.append({
                    'errors': inline_serializer.errors,
                    'identifier': instances[idx].pk if operation == "update_inlines" else idx
                })

    # respond with 400 in case of invalid data.
    if len(serializer_errors):
        raise serializers.ValidationError({"inline_errors": serializer_errors})

    return valid_serializers


def get_related_name(fk):
    """
    returns the name used to link the foreign key relationship.
    """
    if fk._related_name:
        return fk._related_name
    return fk.model._meta.model_name + '_set'
