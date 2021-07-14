from rest_framework import permissions


class IsAdminUser(permissions.BasePermission):

    def has_permission(self, request, view):
        if request.user and request.user.is_authenticated and request.user.is_staff and request.user.is_active:
            return True
        return False
