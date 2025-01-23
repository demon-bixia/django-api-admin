def prepare_lookup_value(key, value, separator=","):
    """
    Return a lookup value prepared to be used in queryset filtering.
    """
    # if key ends with __in, split parameter into separate values
    if key.endswith("__in"):
        value = value.split(separator)
    # if key ends with __isnull, special case '' and the string literals 'false' and '0'
    elif key.endswith("__isnull"):
        value = value.lower() not in ("", "false", "0")
    return value
