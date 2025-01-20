def action(function=None, *, permissions=None, description=None):
    """
    Conveniently add attributes to an action function::

        @admin.action(
            permissions=['publish'],
            description='Mark selected stories as published',
        )
        def make_published(self, request, queryset):
            queryset.update(status='p')

    This is equivalent to setting some attributes (with the original, longer
    names) on the function directly::

        def make_published(self, request, queryset):
            queryset.update(status='p')
        make_published.allowed_permissions = ['publish']
        make_published.short_description = 'Mark selected stories as published'
    """

    def decorator(func):
        if permissions is not None:
            func.allowed_permissions = permissions
        if description is not None:
            func.short_description = description
        return func

    if function is None:
        return decorator
    else:
        return decorator(function)
