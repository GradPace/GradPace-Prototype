from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from django.db import transaction
from django.http import Http404
from django.template.loader import render_to_string
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from drf_spectacular.utils import extend_schema
from rest_framework import generics, permissions, status
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .mail import send_in_background
from .models import Certificate, Skill, StudentProfile, TakenClass
from .serializers import (
    CertificateSerializer,
    LoginSerializer,
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
    TranscriptResultSerializer,
    TranscriptUploadSerializer,
    UserSerializer,
)
from .throttling import AuthRateThrottle
from .transcript import TranscriptError, parse_transcript

User = get_user_model()


def _blacklist_all_outstanding_tokens(user):
    """Force logout everywhere - used after a password change/reset so an
    old/stolen refresh token can't keep minting new access tokens."""
    # One insert for all of them; ignore_conflicts skips tokens that are
    # already blacklisted (BlacklistedToken.token is a OneToOneField).
    BlacklistedToken.objects.bulk_create(
        [BlacklistedToken(token=token) for token in OutstandingToken.objects.filter(user=user)],
        ignore_conflicts=True,
    )


class RegisterView(APIView):
    """Public - creates a user and logs them in immediately (same token shape
    as /login/), so the frontend doesn't need a separate post-signup login."""

    permission_classes = [permissions.AllowAny]
    throttle_classes = [AuthRateThrottle]
    throttle_scope = 'register'

    @extend_schema(request=RegisterSerializer, responses={201: TokenPairSerializer})
    def post(self, request):
        # request in context: Turnstile verification reads the client IP.
        serializer = RegisterSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)
        return Response(
            {'access': str(refresh.access_token), 'refresh': str(refresh)},
            status=status.HTTP_201_CREATED,
        )


class LoginView(TokenObtainPairView):
    """Public - simplejwt's login, with LoginSerializer's Turnstile check in
    front of it. Same response shape as before (access + refresh)."""

    serializer_class = LoginSerializer
    throttle_classes = [AuthRateThrottle]
    throttle_scope = 'login'


class RefreshView(TokenRefreshView):
    """Public - simplejwt's refresh, throttled like the other auth
    endpoints."""

    throttle_classes = [AuthRateThrottle]
    throttle_scope = 'refresh'


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
    throttle_classes = [AuthRateThrottle]
    throttle_scope = 'password_reset'

    @extend_schema(request=PasswordResetRequestSerializer, responses={200: None})
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        try:
            user = User.objects.get(email__lower=serializer.validated_data['email'].lower())
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
        send_in_background(email)

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
        location, target_job, graduated). student_id is not editable here - 404 if no
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


def _skipped(course, reason):
    """A parsed course -> a TranscriptResultSerializer `skipped` entry. Same
    shape as accounts/transcript.py's own skipped rows."""
    return {
        'course_code': course['course_code'],
        'course_name': course['course_name'],
        'semester': course['semester'],
        'year': course['year'],
        'reason': reason,
    }


class TranscriptUploadView(StudentOwnedMixin, APIView):
    """Authenticated - imports the caller's ODU unofficial transcript PDF as
    TakenClass rows (accounts/transcript.py). The PDF is parsed in memory and
    never stored.

    Safe to upload again: a class already on the profile for the same term
    (course_code + semester + year) is skipped, not duplicated. Every row is
    saved or none are."""

    # Multipart for this view only - JSON is the API-wide default (see
    # DEFAULT_PARSER_CLASSES in config/settings/base.py).
    parser_classes = [MultiPartParser]
    # Keyed on the user here, since the caller is authenticated. Parsing a
    # PDF is CPU-heavy.
    throttle_classes = [AuthRateThrottle]
    throttle_scope = 'transcript'
    queryset = TakenClass.objects.all()

    @extend_schema(
        # Spelled out rather than TranscriptUploadSerializer: drf-spectacular
        # documents a FileField as a URL string, so Swagger UI would show a
        # text box instead of a file picker.
        request={
            'multipart/form-data': {
                'type': 'object',
                'properties': {
                    'file': {'type': 'string', 'format': 'binary'},
                    'dry_run': {'type': 'boolean', 'default': False},
                },
                'required': ['file'],
            }
        },
        responses={201: TranscriptResultSerializer, 200: TranscriptResultSerializer},
    )
    def post(self, request):
        """Upload `file` (the PDF). 201 with the saved classes, or 200 with
        what would be saved when `dry_run` is true. 400 if the file isn't a
        readable transcript."""
        profile = self.get_student_profile()
        upload = TranscriptUploadSerializer(data=request.data)
        upload.is_valid(raise_exception=True)

        try:
            parsed = parse_transcript(upload.validated_data['file'])
        except TranscriptError as exc:
            return Response({'file': [str(exc)]}, status=status.HTTP_400_BAD_REQUEST)

        on_profile = set(self.get_queryset().values_list('course_code', 'semester', 'year'))
        in_upload = set()
        skipped = list(parsed.skipped)
        rows = []
        for course in parsed.courses:
            key = (course['course_code'], course['semester'], course['year'])
            if key in on_profile:
                skipped.append(_skipped(course, 'Already on your profile.'))
            elif key in in_upload:
                # e.g. a class listed both as graded and as in progress.
                skipped.append(_skipped(course, 'Listed twice for the same term.'))
            else:
                in_upload.add(key)
                rows.append(TakenClassSerializer(data=course))

        valid = []
        for row in rows:
            if row.is_valid():
                valid.append(row)
            else:
                errors = ' '.join(str(error) for field in row.errors.values() for error in field)
                skipped.append(_skipped(row.initial_data, errors))

        if upload.validated_data['dry_run']:
            courses = [row.initial_data for row in valid]
            response_status = status.HTTP_200_OK
        else:
            with transaction.atomic():
                created = TakenClass.objects.bulk_create(
                    TakenClass(student=profile, **row.validated_data) for row in valid
                )
            courses = TakenClassSerializer(created, many=True).data
            response_status = status.HTTP_201_CREATED

        return Response(
            {'courses': courses, 'skipped': skipped, 'unparsed': parsed.unparsed},
            status=response_status,
        )


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
