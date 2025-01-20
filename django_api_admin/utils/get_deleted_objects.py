from django.db import router
from django.urls import NoReverseMatch, reverse
from django.utils.html import format_html
from django.utils.text import capfirst

from django_api_admin.utils.quote import quote
from django_api_admin.utils.nested_objects import NestedObjects


def get_deleted_objects(objs, request, admin_site):
    """
    Find all objects related to ``objs`` that should also be deleted. ``objs``
    must be a homogeneous iterable of objects (e.g. a QuerySet).

    Return a nested list of strings suitable for display in the
    template with the ``unordered_list`` filter.
    """
    try:
        obj = objs[0]
    except IndexError:
        return [], {}, set(), []
    else:
        using = router.db_for_write(obj._meta.model)
    collector = NestedObjects(using=using, origin=objs)
    collector.collect(objs)
    perms_needed = set()

    def format_callback(obj):
        model = obj.__class__
        has_admin = model in admin_site._registry
        opts = obj._meta

        no_edit_link = "%s: %s" % (capfirst(opts.verbose_name), obj)

        if has_admin:
            if not admin_site._registry[model].has_delete_permission(request):
                perms_needed.add(opts.verbose_name)
            try:
                admin_url = reverse(
                    "%s:%s_%s_change"
                    % (admin_site.name, opts.app_label, opts.model_name),
                    None,
                    (quote(obj.pk),),
                )
            except NoReverseMatch:
                # Change url doesn't exist -- don't display link to edit
                return no_edit_link

            # Display a link to the admin page.
            return format_html(
                '{}: <a href="{}">{}</a>', capfirst(
                    opts.verbose_name), admin_url, obj
            )
        else:
            # Don't display link to edit, because it either has no
            # admin or is edited inline.
            return no_edit_link

    to_delete = collector.nested(format_callback)

    protected = [format_callback(obj) for obj in collector.protected]
    model_count = {
        model._meta.verbose_name_plural: len(objs)
        for model, objs in collector.model_objs.items()
    }

    return to_delete, model_count, perms_needed, protected
