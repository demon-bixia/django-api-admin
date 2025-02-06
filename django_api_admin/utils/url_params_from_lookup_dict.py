def url_params_from_lookup_dict(lookups):
    """
    Convert the type of lookups specified in a ForeignKey limit_choices_to
    attribute to a dictionary of query parameters
    """
    params = {}
    if lookups and hasattr(lookups, "items"):
        for k, v in lookups.items():
            if callable(v):
                v = v()
            if isinstance(v, (tuple, list)):
                v = ",".join(str(x) for x in v)
            elif isinstance(v, bool):
                v = ("0", "1")[v]
            else:
                v = str(v)
            params[k] = v
    return params
