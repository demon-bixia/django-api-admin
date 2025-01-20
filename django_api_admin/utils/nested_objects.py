from collections import defaultdict

from django.db import models
from django.db.models.deletion import Collector


class NestedObjects(Collector):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.edges = {}  # {from_instance: [to_instances]}
        self.protected = set()
        self.model_objs = defaultdict(set)

    def add_edge(self, source, target):
        self.edges.setdefault(source, []).append(target)

    def collect(self, objs, source=None, source_attr=None, **kwargs):
        for obj in objs:
            if source_attr and not source_attr.endswith("+"):
                related_name = source_attr % {
                    "class": source._meta.model_name,
                    "app_label": source._meta.app_label,
                }
                self.add_edge(getattr(obj, related_name), obj)
            else:
                self.add_edge(None, obj)
            self.model_objs[obj._meta.model].add(obj)
        try:
            return super().collect(objs, source_attr=source_attr, **kwargs)
        except models.ProtectedError as e:
            self.protected.update(e.protected_objects)
        except models.RestrictedError as e:
            self.protected.update(e.restricted_objects)

    def related_objects(self, related_model, related_fields, objs):
        qs = super().related_objects(related_model, related_fields, objs)
        return qs.select_related(
            *[related_field.name for related_field in related_fields]
        )

    def _nested(self, obj, seen, format_callback):
        if obj in seen:
            return []
        seen.add(obj)
        children = []
        for child in self.edges.get(obj, ()):
            children.extend(self._nested(child, seen, format_callback))
        if format_callback:
            ret = [format_callback(obj)]
        else:
            ret = [obj]
        if children:
            ret.append(children)
        return ret

    def nested(self, format_callback=None):
        """
        Return the graph as a nested list.
        """
        seen = set()
        roots = []
        for root in self.edges.get(None, ()):
            roots.extend(self._nested(root, seen, format_callback))
        return roots

    def can_fast_delete(self, *args, **kwargs):
        """
        We always want to load the objects into memory so that we can display
        them to the user in confirm page.
        """
        return False
