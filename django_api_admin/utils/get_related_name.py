from django.utils.translation import gettext_lazy as _


def get_related_name(fk):
    """
    returns the name used to link the foreign key relationship.
    """
    if fk._related_name:
        return fk._related_name
    return fk.model._meta.model_name + '_set'
