from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import (
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
)

User = get_user_model()


def _blacklist_all_outstanding_tokens(user):
    """Force logout everywhere - used after a password change/reset so an
    old/stolen refresh token can't keep minting new access tokens."""
    for outstanding in OutstandingToken.objects.filter(user=user):
        BlacklistedToken.objects.get_or_create(token=outstanding)


class RegisterView(APIView):
    """Public - creates a user and logs them in immediately (same token shape
    as /login/), so the frontend doesn't need a separate post-signup login."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)
        return Response(
            {"access": str(refresh.access_token), "refresh": str(refresh)},
            status=status.HTTP_201_CREATED,
        )


class LogoutView(APIView):
    """Authenticated (default IsAuthenticated) - blacklists the given refresh
    token so it can no longer be used at /refresh/. Needs BLACKLIST_AFTER_ROTATION's
    token_blacklist app - see SIMPLE_JWT in config/settings/base.py.

    Only blacklists the refresh token passed in; the access token used to
    authenticate this request stays valid until it naturally expires (a
    short window - ACCESS_TOKEN_LIFETIME - not worth adding a second
    blacklist check on every authenticated request to close)."""

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {"refresh": "This field is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            RefreshToken(refresh_token).blacklist()
        except TokenError:
            return Response(
                {"refresh": "Invalid or expired token."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(status=status.HTTP_205_RESET_CONTENT)


class PasswordChangeView(APIView):
    """Authenticated (default IsAuthenticated) - requires the current
    password. Also blacklists every other outstanding refresh token for the
    user: a password change should force re-login on every other session."""

    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        _blacklist_all_outstanding_tokens(user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PasswordResetRequestView(APIView):
    """Public. Always returns 200, whether or not the email is registered -
    the response can't be used to enumerate accounts. If it is registered,
    emails a reset link built from settings.FRONTEND_URL."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = User.objects.get(email__iexact=serializer.validated_data["email"])
        except User.DoesNotExist:
            return Response(status=status.HTTP_200_OK)

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        reset_url = f"{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}"
        context = {"reset_url": reset_url}

        # Plain-text part first (some clients/spam filters want it) with the
        # HTML version attached as an alternative, not HTML-only.
        text_body = render_to_string("accounts/emails/password_reset.txt", context)
        html_body = render_to_string("accounts/emails/password_reset.html", context)

        email = EmailMultiAlternatives(
            subject="Reset your GradPace password",
            body=text_body,
            to=[user.email],  # from_email defaults to DEFAULT_FROM_EMAIL
        )
        email.attach_alternative(html_body, "text/html")
        email.send()

        return Response(status=status.HTTP_200_OK)


class PasswordResetConfirmView(APIView):
    """Public - the uid+token pair from the emailed link IS the
    authentication here, in place of a logged-in session."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        _blacklist_all_outstanding_tokens(user)
        return Response(status=status.HTTP_200_OK)


class MeView(APIView):
    """Protected - proves a simplejwt access token authenticates correctly."""

    def get(self, request):
        return Response(
            {
                "id": request.user.pk,
                "username": request.user.username,
                "email": request.user.email,
            }
        )
