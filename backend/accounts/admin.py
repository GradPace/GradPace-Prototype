from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (
    AdminProfile,
    AlumniProfile,
    Certificate,
    CustomUser,
    Role,
    Skill,
    StudentProfile,
    TakenClass,
)


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    """UserAdmin's default fieldsets/list assume `username` - override for
    our email-only, no-username CustomUser."""

    model = CustomUser
    ordering = ['email']
    list_display = ['email', 'first_name', 'last_name', 'role', 'is_staff']
    # first_name/last_name are encrypted at rest, so the database can't
    # search them - only email.
    search_fields = ['email']
    fieldsets = [
        (None, {'fields': ['email', 'password']}),
        ('Personal info', {'fields': ['first_name', 'last_name', 'role']}),
        (
            'Permissions',
            {'fields': ['is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions']},
        ),
        ('Important dates', {'fields': ['last_login', 'created_at']}),
    ]
    add_fieldsets = [
        (
            None,
            {
                'classes': ['wide'],
                'fields': ['email', 'password1', 'password2', 'role'],
            },
        ),
    ]
    readonly_fields = ['created_at']


admin.site.register(Role)
admin.site.register(StudentProfile)
admin.site.register(AlumniProfile)
admin.site.register(AdminProfile)
admin.site.register(TakenClass)
admin.site.register(Certificate)
admin.site.register(Skill)
