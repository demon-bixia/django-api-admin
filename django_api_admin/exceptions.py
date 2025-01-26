from django.core.exceptions import SuspiciousOperation


class NotRelationField(Exception):
    pass


class DisallowedModelAdminLookup(SuspiciousOperation):
    """Invalid filter was passed to admin view via URL querystring"""
    pass


class IncorrectLookupParameters(Exception):
    pass


class NotRelationField(Exception):
    pass


class FieldIsAForeignKeyColumnName(Exception):
    """A field is a foreign key attname, i.e. <FK>_id."""
    pass


class AlreadyRegistered(Exception):
    pass


class NotRegistered(Exception):
    pass
