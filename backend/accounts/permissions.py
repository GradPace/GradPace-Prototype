from rest_framework import permissions

from . import roles


class HasRole(permissions.BasePermission):
    """Allows only authenticated users whose Role is `role`. Subclasses set
    `role` (one of accounts/roles.py) and `message` (shown with the 403)."""

    role = None

    def has_permission(self, request, view):
        user_role = getattr(request.user, 'role', None)
        return bool(
            request.user.is_authenticated and user_role and user_role.role_name == self.role
        )


class IsStudent(HasRole):
    """Only student accounts. Used by alumni conversion."""

    role = roles.STUDENT
    message = 'Only students can convert to alumni.'


class IsAlumni(HasRole):
    """Only alumni accounts. Students get this role
    through alumni conversion (AlumniConversionView)."""

    role = roles.ALUMNI
    message = 'Only alumni can take the alumni survey.'


class IsAdmin(HasRole):
    """Only admin accounts. Users get this role through the make_admin
    management command."""

    role = roles.ADMIN
    message = 'Only admins can do this.'
