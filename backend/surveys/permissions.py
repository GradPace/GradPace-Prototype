from rest_framework import permissions


class IsAlumni(permissions.BasePermission):
    """Only users with the 'alumni' role (spec FR-3.1.1.6.2-01). How a user
    gets that role is decided elsewhere. This only checks it."""

    message = 'Only alumni can take the alumni survey.'

    def has_permission(self, request, view):
        role = getattr(request.user, 'role', None)
        return bool(request.user.is_authenticated and role and role.role_name == 'alumni')
