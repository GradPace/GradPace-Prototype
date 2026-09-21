from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from django.http import Http404
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Certificate, Skill, StudentProfile, TakenClass
from .serializers import (
    CertificateSerializer,
    LogoutSerializer,
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    SkillSerializer,
    StudentProfileCreateSerializer,
    StudentProfileSerializer,
    StudentProfileUpdateSerializer,
    TakenClassSerializer,
    TokenPairSerializer,
    UserSerializer,
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

    @extend_schema(request=RegisterSerializer, responses={201: TokenPairSerializer})
    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)
        return Response(
            {'access': str(refresh.access_token), 'refresh': str(refresh)},
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

    @extend_schema(request=LogoutSerializer, responses={205: None})
    def post(self, request):
        serializer = LogoutSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            RefreshToken(serializer.validated_data['refresh']).blacklist()
        except TokenError:
            return Response(
                {'refresh': 'Invalid or expired token.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        return Response(status=status.HTTP_205_RESET_CONTENT)


class PasswordChangeView(APIView):
    """Authenticated (default IsAuthenticated) - requires the current
    password. Also blacklists every other outstanding refresh token for the
    user: a password change should force re-login on every other session."""

    @extend_schema(request=PasswordChangeSerializer, responses={204: None})
    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        _blacklist_all_outstanding_tokens(user)
        return Response(status=status.HTTP_204_NO_CONTENT)


class PasswordResetRequestView(APIView):
    """Public. Always returns 200, whether or not the email is registered -
    the response can't be used to enumerate accounts. If it is registered,
    emails a reset link built from settings.FRONTEND_URL."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(request=PasswordResetRequestSerializer, responses={200: None})
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = User.objects.get(email__iexact=serializer.validated_data['email'])
        except User.DoesNotExist:
            return Response(status=status.HTTP_200_OK)

        uid = urlsafe_base64_encode(force_bytes(user.pk))
        token = default_token_generator.make_token(user)
        reset_url = f'{settings.FRONTEND_URL}/reset-password?uid={uid}&token={token}'
        context = {'reset_url': reset_url}

        # Plain-text part first (some clients/spam filters want it) with the
        # HTML version attached as an alternative, not HTML-only.
        text_body = render_to_string('accounts/emails/password_reset.txt', context)
        html_body = render_to_string('accounts/emails/password_reset.html', context)

        email = EmailMultiAlternatives(
            subject='Reset your GradPace password',
            body=text_body,
            to=[user.email],  # from_email defaults to DEFAULT_FROM_EMAIL
        )
        email.attach_alternative(html_body, 'text/html')
        email.send()

        return Response(status=status.HTTP_200_OK)


class PasswordResetConfirmView(APIView):
    """Public - the uid+token pair from the emailed link IS the
    authentication here, in place of a logged-in session."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(request=PasswordResetConfirmSerializer, responses={200: None})
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        _blacklist_all_outstanding_tokens(user)
        return Response(status=status.HTTP_200_OK)


class MeView(APIView):
    """Protected - proves a simplejwt access token authenticates correctly."""

    @extend_schema(responses={200: UserSerializer})
    def get(self, request):
        return Response(UserSerializer(request.user).data)


class ProfileView(APIView):
    """Authenticated (default IsAuthenticated) - the caller's own
    StudentProfile. One per user: POST creates it (404s on GET/PATCH until
    then), PATCH partially updates the mutable fields."""

    @extend_schema(responses={200: StudentProfileSerializer})
    def get(self, request):
        """Fetch the caller's own student profile. 404 if they haven't
        created one yet (POST to this same URL first)."""
        try:
            profile = request.user.student_profile
        except StudentProfile.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(StudentProfileSerializer(profile).data)

    @extend_schema(
        request=StudentProfileCreateSerializer, responses={201: StudentProfileSerializer}
    )
    def post(self, request):
        """Create the caller's student profile. One-time only - 400s if a
        profile already exists for this user. Sets student_id, which is
        permanent after this (see PATCH)."""
        if StudentProfile.objects.filter(user=request.user).exists():
            return Response(
                {'detail': 'Profile already exists.'}, status=status.HTTP_400_BAD_REQUEST
            )
        serializer = StudentProfileCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        profile = serializer.save()
        return Response(StudentProfileSerializer(profile).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        request=StudentProfileUpdateSerializer, responses={200: StudentProfileSerializer}
    )
    def patch(self, request):
        """Partially update the caller's student profile (name, major, uni,
        location, graduated). student_id is not editable here - 404 if no
        profile exists yet."""
        try:
            profile = request.user.student_profile
        except StudentProfile.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = StudentProfileUpdateSerializer(profile, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        profile = serializer.save()
        return Response(StudentProfileSerializer(profile).data)


class StudentOwnedMixin:
    """Shared by the taken-class/certificate/skill views below - scopes
    every query to the caller's own StudentProfile, 404ing (not 403) before
    one exists or when the entry belongs to someone else. Same profile-first
    behavior as ProfileView.

    Views using this mixin set `queryset = <Model>.objects.all()` purely to
    declare the model (for get_queryset() and schema generation) - it's
    never queried directly since get_queryset() always filters by owner."""

    def get_student_profile(self):
        try:
            return self.request.user.student_profile
        except StudentProfile.DoesNotExist:
            raise Http404 from None

    def get_queryset(self):
        return self.queryset.model.objects.filter(student=self.get_student_profile())

    def perform_create(self, serializer):
        serializer.save(student=self.get_student_profile())


class TakenClassListView(StudentOwnedMixin, generics.ListCreateAPIView):
    """Authenticated (default IsAuthenticated) - the caller's own taken
    classes. GET lists them, POST adds one."""

    serializer_class = TakenClassSerializer
    queryset = TakenClass.objects.all()


class TakenClassDetailView(StudentOwnedMixin, generics.RetrieveUpdateDestroyAPIView):
    """Authenticated - a single taken-class entry, scoped to the caller."""

    serializer_class = TakenClassSerializer
    queryset = TakenClass.objects.all()


class CertificateListView(StudentOwnedMixin, generics.ListCreateAPIView):
    """Authenticated - the caller's own certificates. GET lists them, POST
    adds one."""

    serializer_class = CertificateSerializer
    queryset = Certificate.objects.all()


class CertificateDetailView(StudentOwnedMixin, generics.RetrieveUpdateDestroyAPIView):
    """Authenticated - a single certificate entry, scoped to the caller."""

    serializer_class = CertificateSerializer
    queryset = Certificate.objects.all()


class SkillListView(StudentOwnedMixin, generics.ListCreateAPIView):
    """Authenticated - the caller's own skills. GET lists them, POST adds
    one (400s on a duplicate name - see Skill's unique_together)."""

    serializer_class = SkillSerializer
    queryset = Skill.objects.all()


class SkillDetailView(StudentOwnedMixin, generics.RetrieveUpdateDestroyAPIView):
    """Authenticated - a single skill entry, scoped to the caller."""

    serializer_class = SkillSerializer
    queryset = Skill.objects.all()
