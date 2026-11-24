from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import (
    AdminProfile,
    AlumniProfile,
    Certificate,
    CustomUser,
    Role,
    SiteSettings,
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


@admin.register(SiteSettings)
class SiteSettingsAdmin(admin.ModelAdmin):
    """Read-only. Admins change these from the dashboard
    (/api/auth/admin/settings/), which records who changed them."""

    list_display = ['require_email_verification', 'updated_at', 'updated_by']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
