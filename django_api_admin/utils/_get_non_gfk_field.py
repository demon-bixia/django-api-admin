from django.core.exceptions import FieldDoesNotExist
from django_api_admin.exceptions import FieldIsAForeignKeyColumnName


def _get_non_gfk_field(opts, name):
    """
    For historical reasons, the admin app relies on GenericForeignKeys as being
    "not found" by get_field(). This could likely be cleaned up.
    Reverse relations should also be excluded as these aren't attributes of the
    model (rather something like `foo_set`).
    """
    field = opts.get_field(name)
    if (
        field.is_relation
        and
        # Generic foreign keys OR reverse relations
        ((field.many_to_one and not field.related_model) or field.one_to_many)
    ):
        raise FieldDoesNotExist()

    # Avoid coercing <FK>_id fields to FK
    if (
        field.is_relation
        and not field.many_to_many
        and hasattr(field, "attname")
        and field.attname == name
    ):
        raise FieldIsAForeignKeyColumnName()

    return field
