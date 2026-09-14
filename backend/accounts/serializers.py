from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from rest_framework import serializers

from .models import StudentProfile

User = get_user_model()

# Shared by every serializer that accepts a new password (max_length caps
# hashing cost on an absurdly long input - a DoS angle, not a security
# control on its own - see AUTH_PASSWORD_VALIDATORS for the real rules).
PASSWORD_FIELD_KWARGS = {"write_only": True, "max_length": 64}


def run_password_validators(password, user=None):
    """AUTH_PASSWORD_VALIDATORS raises Django's ValidationError, not DRF's -
    translate it, and raise under the "password" key so callers can just
    ``raise serializers.ValidationError({"password": ...})``-style attach it."""
    try:
        validate_password(password, user=user)
    except DjangoValidationError as exc:
        raise serializers.ValidationError({"password": list(exc.messages)})


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=150)
    email = serializers.EmailField()
    password = serializers.CharField(**PASSWORD_FIELD_KWARGS)
    password_confirm = serializers.CharField(**PASSWORD_FIELD_KWARGS)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("A user with that username already exists.")
        return value

    def validate_email(self, value):
        # iexact - must match PasswordResetRequestView's lookup, or two users
        # differing only by email case (Foo@x.com / foo@x.com) could both
        # register, and a reset request for either raises MultipleObjectsReturned.
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError("A user with that email already exists.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirm"]:
            raise serializers.ValidationError({"password_confirm": "Passwords do not match."})
        run_password_validators(attrs["password"])
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(
            username=validated_data["username"],
            email=validated_data["email"],
            password=validated_data["password"],
        )


class PasswordChangeSerializer(serializers.Serializer):
    """Requires the caller's current password - used by PasswordChangeView,
    which is authenticated, so ``self.context["request"].user`` is real."""

    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(**PASSWORD_FIELD_KWARGS)
    new_password_confirm = serializers.CharField(**PASSWORD_FIELD_KWARGS)

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError("Current password is incorrect.")
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError({"new_password_confirm": "Passwords do not match."})
        run_password_validators(attrs["new_password"], user=self.context["request"].user)
        return attrs

    def save(self):
        user = self.context["request"].user
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
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
        except (TypeError, ValueError, OverflowError, User.DoesNotExist):
            raise serializers.ValidationError("Invalid reset link.")
        return value

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError({"new_password_confirm": "Passwords do not match."})

        # validate_uid runs first (field validators run before validate()) and
        # stashes the user on self._user - re-check defensively regardless.
        user = getattr(self, "_user", None)
        if user is None:
            raise serializers.ValidationError({"uid": "Invalid reset link."})

        if not default_token_generator.check_token(user, attrs["token"]):
            raise serializers.ValidationError({"token": "Invalid or expired reset link."})

        run_password_validators(attrs["new_password"], user=user)
        attrs["user"] = user
        return attrs

    def save(self):
        user = self.validated_data["user"]
        user.set_password(self.validated_data["new_password"])
        user.save(update_fields=["password"])
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
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)


class StudentProfileSerializer(serializers.ModelSerializer):
    """Read/response shape - includes first/last name from User even though
    they live outside StudentProfile, since a profile view is naturally where
    a frontend wants them alongside the student-specific fields."""

    first_name = serializers.CharField(source="user.first_name")
    last_name = serializers.CharField(source="user.last_name")

    class Meta:
        model = StudentProfile
        fields = ["student_id", "first_name", "last_name", "major", "minor", "graduation_year"]


class StudentProfileCreateSerializer(serializers.ModelSerializer):
    """Creates the caller's own profile - student_id is set once here and is
    not editable afterwards (see StudentProfileUpdateSerializer)."""

    first_name = serializers.CharField(source="user.first_name", required=False, allow_blank=True)
    last_name = serializers.CharField(source="user.last_name", required=False, allow_blank=True)

    class Meta:
        model = StudentProfile
        fields = ["student_id", "first_name", "last_name", "major", "minor", "graduation_year"]

    def create(self, validated_data):
        user_data = validated_data.pop("user", {})
        user = self.context["request"].user
        if user_data:
            for attr, value in user_data.items():
                setattr(user, attr, value)
            user.save(update_fields=list(user_data.keys()))
        return StudentProfile.objects.create(user=user, **validated_data)


class StudentProfileUpdateSerializer(serializers.ModelSerializer):
    """Partial update of the caller's own profile. No student_id field -
    school-issued, not something a student can change themselves."""

    first_name = serializers.CharField(source="user.first_name", required=False, allow_blank=True)
    last_name = serializers.CharField(source="user.last_name", required=False, allow_blank=True)

    class Meta:
        model = StudentProfile
        fields = ["first_name", "last_name", "major", "minor", "graduation_year"]

    def update(self, instance, validated_data):
        user_data = validated_data.pop("user", {})
        if user_data:
            for attr, value in user_data.items():
                setattr(instance.user, attr, value)
            instance.user.save(update_fields=list(user_data.keys()))
        return super().update(instance, validated_data)
