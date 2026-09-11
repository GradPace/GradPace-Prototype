from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from .serializers import RegisterSerializer


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
