from rest_framework import permissions


class IsAdminUser(permissions.BasePermission):

    def has_permission(self, request, view):
        return self.is_superuser(request)

    def is_superuser(self, request):
        return bool(request.user and request.user.is_authenticated and request.user.is_staff and request.user.is_active)
