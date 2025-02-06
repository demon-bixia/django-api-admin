from django.core.exceptions import FieldDoesNotExist
from django_api_admin.constants.vars import LOOKUP_SEP


def lookup_spawns_duplicates(opts, lookup_path):
    """
    Return True if the given lookup path spawns duplicates.
    """
    lookup_fields = lookup_path.split(LOOKUP_SEP)
    # Go through the fields (following all relations) and look for an m2m.
    for field_name in lookup_fields:
        if field_name == "pk":
            field_name = opts.pk.name
        try:
            field = opts.get_field(field_name)
        except FieldDoesNotExist:
            # Ignore query lookups.
            continue
        else:
            if hasattr(field, "path_infos"):
                # This field is a relation; update opts to follow the relation.
                path_info = field.path_infos
                opts = path_info[-1].to_opts
                if any(path.m2m for path in path_info):
                    # This field is a m2m relation so duplicates must be
                    # handled.
                    return True
    return False
