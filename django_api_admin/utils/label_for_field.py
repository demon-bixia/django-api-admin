from django.core.exceptions import FieldDoesNotExist
from django.forms.utils import pretty_name

from django_api_admin.utils._get_non_gfk_field import _get_non_gfk_field
from django_api_admin.exceptions import FieldIsAForeignKeyColumnName


def label_for_field(name, model, model_admin=None, return_attr=False, form=None):
    """
    Return a sensible label for a field name. The name can be a callable,
    property (but not created with @property decorator), or the name of an
    object's attribute, as well as a model field. If return_attr is True, also
    return the resolved attribute (which could be a callable). This will be
    None if (and only if) the name refers to a field.
    """
    attr = None
    try:
        field = _get_non_gfk_field(model._meta, name)
        try:
            label = field.verbose_name
        except AttributeError:
            # field is likely a ForeignObjectRel
            label = field.related_model._meta.verbose_name
    except FieldDoesNotExist:
        if name == "__str__":
            label = str(model._meta.verbose_name)
            attr = str
        else:
            if callable(name):
                attr = name
            elif hasattr(model_admin, name):
                attr = getattr(model_admin, name)
            elif hasattr(model, name):
                attr = getattr(model, name)
            elif form and name in form.fields:
                attr = form.fields[name]
            else:
                message = "Unable to lookup '%s' on %s" % (
                    name,
                    model._meta.object_name,
                )
                if model_admin:
                    message += " or %s" % model_admin.__class__.__name__
                if form:
                    message += " or %s" % form.__class__.__name__
                raise AttributeError(message)

            if hasattr(attr, "short_description"):
                label = attr.short_description
            elif (
                isinstance(attr, property)
                and hasattr(attr, "fget")
                and hasattr(attr.fget, "short_description")
            ):
                label = attr.fget.short_description
            elif callable(attr):
                if attr.__name__ == "<lambda>":
                    label = "--"
                else:
                    label = pretty_name(attr.__name__)
            else:
                label = pretty_name(name)
    except FieldIsAForeignKeyColumnName:
        label = pretty_name(name)
        attr = name

    if return_attr:
        return (label, attr)
    else:
        return label
