"""Auth-flow serializers (register/login support/password/logout) - not
tied to any one role. Role-specific profile serializers live in their own
modules (e.g. student.py)."""

from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from ..models import Role
from ..turnstile import TOKEN_FIELD, verify_turnstile

User = get_user_model()

# Shared by every serializer that accepts a new password (max_length caps
# hashing cost on an absurdly long input - a DoS angle, not a security
# control on its own - see AUTH_PASSWORD_VALIDATORS for the real rules).
PASSWORD_FIELD_KWARGS = {'write_only': True, 'max_length': 64}

# The Turnstile widget's token (see accounts/turnstile.py). Not `required` at
# the field level - verify_turnstile() runs from validate() instead, since a
# missing field would skip a validate_<field>() method entirely, and it's
# skipped altogether when TURNSTILE_ENABLED is off (the test suite).
TURNSTILE_FIELD_KWARGS = {'write_only': True, 'required': False, 'allow_blank': True}


def run_password_validators(password, user=None):
    """AUTH_PASSWORD_VALIDATORS raises Django's ValidationError, not DRF's -
    translate it, and raise under the "password" key so callers can just
    ``raise serializers.ValidationError({"password": ...})``-style attach it."""
    try:
        validate_password(password, user=user)
    except DjangoValidationError as exc:
        raise serializers.ValidationError({'password': list(exc.messages)}) from exc


class RegisterSerializer(serializers.Serializer):
    """Public registration - always creates a student. Alumni/admin accounts
    are provisioned some other way (not self-service), so there's no role
    field to accept here."""

    first_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    email = serializers.EmailField()
    password = serializers.CharField(**PASSWORD_FIELD_KWARGS)
    password_confirm = serializers.CharField(**PASSWORD_FIELD_KWARGS)
    cf_turnstile_response = serializers.CharField(**TURNSTILE_FIELD_KWARGS)

    def validate_email(self, value):
        # Case-insensitive, like the unique_email_ci constraint - which also
        # catches two concurrent registrations that both get past this check.
        if User.objects.filter(email__lower=value.lower()).exists():
            raise serializers.ValidationError('A user with that email already exists.')
        return value

    def validate(self, attrs):
        # First - before the password validators, one of which calls out to
        # Have I Been Pwned.
        verify_turnstile(
            attrs.pop(TOKEN_FIELD, ''), action='register', request=self.context.get('request')
        )
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password_confirm': 'Passwords do not match.'})
        run_password_validators(attrs['password'])
        return attrs

    def create(self, validated_data):
        student_role, _ = Role.objects.get_or_create(role_name='student')
        try:
            # atomic: a failed insert mustn't break an enclosing transaction.
            with transaction.atomic():
                return User.objects.create_user(
                    email=validated_data['email'],
                    password=validated_data['password'],
                    first_name=validated_data.get('first_name', ''),
                    last_name=validated_data.get('last_name', ''),
                    role=student_role,
                )
        except IntegrityError:
            # Lost a race with a concurrent registration for the same email
            # (unique_email_ci) - same response as validate_email's.
            raise serializers.ValidationError(
                {'email': 'A user with that email already exists.'}
            ) from None


class LoginSerializer(TokenObtainPairSerializer):
    """simplejwt's email/password -> token pair, plus a Turnstile check that
    runs before authenticate() so a bot never gets as far as password
    hashing."""

    cf_turnstile_response = serializers.CharField(**TURNSTILE_FIELD_KWARGS)

    def validate(self, attrs):
        verify_turnstile(
            attrs.pop(TOKEN_FIELD, ''), action='login', request=self.context.get('request')
        )
        return super().validate(attrs)


class PasswordChangeSerializer(serializers.Serializer):
    """Requires the caller's current password - used by PasswordChangeView,
    which is authenticated, so ``self.context["request"].user`` is real."""

    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(**PASSWORD_FIELD_KWARGS)
    new_password_confirm = serializers.CharField(**PASSWORD_FIELD_KWARGS)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Current password is incorrect.')
        return value

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({'new_password_confirm': 'Passwords do not match.'})
        run_password_validators(attrs['new_password'], user=self.context['request'].user)
        return attrs

    def save(self):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save(update_fields=['password'])
        return user


class PasswordResetRequestSerializer(serializers.Serializer):
    """No validate_email existence check on purpose - PasswordResetRequestView
    returns the same response whether or not the email is registered, so
    submitting a form here can't be used to enumerate accounts."""

    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField()
    token = serializers.CharField()
    new_password = serializers.CharField(**PASSWORD_FIELD_KWARGS)
    new_password_confirm = serializers.CharField(**PASSWORD_FIELD_KWARGS)

    def validate_uid(self, value):
        try:
            user_id = force_str(urlsafe_base64_decode(value))
            self._user = User.objects.get(pk=user_id)
        except TypeError, ValueError, OverflowError, User.DoesNotExist:
            raise serializers.ValidationError('Invalid reset link.') from None
        return value

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({'new_password_confirm': 'Passwords do not match.'})

        # validate_uid runs first (field validators run before validate()) and
        # stashes the user on self._user - re-check defensively regardless.
        user = getattr(self, '_user', None)
        if user is None:
            raise serializers.ValidationError({'uid': 'Invalid reset link.'})

        if not default_token_generator.check_token(user, attrs['token']):
            raise serializers.ValidationError({'token': 'Invalid or expired reset link.'})

        run_password_validators(attrs['new_password'], user=user)
        attrs['user'] = user
        return attrs

    def save(self):
        user = self.validated_data['user']
        user.set_password(self.validated_data['new_password'])
        user.save(update_fields=['password'])
        return user


class LogoutSerializer(serializers.Serializer):
    refresh = serializers.CharField()


# Response-only serializers, for drf-spectacular. RegisterView and MeView are
# plain APIViews that build a dict by hand rather than serializing a model
# instance, so there's nothing for the schema generator to introspect without
# these - see the @extend_schema(responses=...) calls in accounts/views.py.


class TokenPairSerializer(serializers.Serializer):
    access = serializers.CharField(read_only=True)
    refresh = serializers.CharField(read_only=True)


class UserSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    email = serializers.EmailField(read_only=True)
    first_name = serializers.CharField(read_only=True)
    last_name = serializers.CharField(read_only=True)
    role = serializers.CharField(source='role.role_name', read_only=True, allow_null=True)
