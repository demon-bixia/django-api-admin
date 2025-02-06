from django_api_admin.exceptions import NotRelationField


def get_model_from_relation(field):
    if hasattr(field, "path_infos"):
        return field.path_infos[-1].to_opts.model
    else:
        raise NotRelationField
