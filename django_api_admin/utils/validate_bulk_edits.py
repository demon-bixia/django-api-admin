from django.utils.translation import gettext_lazy as _
from django.forms.models import _get_foreign_key

from django_api_admin.utils.validate_inline_field_names import validate_inline_field_names
from django_api_admin.utils.get_inline_by_field_name import get_inline_by_field_name
from django_api_admin.utils.get_related_name import get_related_name


from rest_framework import serializers


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
        inline_serializer_class = inline_admin.get_serializer_class()

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
            serializer_class = inline_admin.get_serializer_class()
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
