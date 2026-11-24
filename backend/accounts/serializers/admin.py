"""Admin dashboard (GP-62) - managing other users' accounts and the
site-wide settings."""

from django.contrib.auth import get_user_model
from rest_framework import serializers

from ..models import SiteSettings

User = get_user_model()


class AdminSettingsSerializer(serializers.ModelSerializer):
    """require_email_verification is the only field an admin can change;
    anything else sent is ignored. updated_by is set by the view."""

    updated_by = serializers.EmailField(source='updated_by.email', read_only=True, allow_null=True)

    class Meta:
        model = SiteSettings
        fields = ['require_email_verification', 'updated_at', 'updated_by']
        read_only_fields = ['updated_at']


class AdminUserSerializer(serializers.ModelSerializer):
    """One row of the admin's user list. is_active is the only field an
    admin can change (deactivate/reactivate); anything else sent is ignored."""

    role = serializers.CharField(source='role.role_name', read_only=True, allow_null=True)
    date_joined = serializers.DateTimeField(source='created_at', read_only=True)

    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'email', 'role', 'date_joined', 'is_active']
        read_only_fields = ['id', 'first_name', 'last_name', 'email']

    def validate_is_active(self, value):
        # Would lock the admin out, possibly leaving no one to undo it.
        if not value and self.instance == self.context['request'].user:
            raise serializers.ValidationError("You can't deactivate your own account.")
        return value
