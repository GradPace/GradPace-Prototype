from django.db import IntegrityError, transaction
from drf_spectacular.utils import extend_schema
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import AlumniSurveyResponse
from .permissions import IsAlumni
from .serializers import AlumniSurveyResponseSerializer

ALREADY_SUBMITTED = {'detail': 'Survey already submitted.'}


class AlumniSurveyView(APIView):
    """Alumni only (403 otherwise). The caller's own Alumni Survey
    response. One per alum and final: POST submits it, a second POST 400s.
    GET returns it, or 404s until it's been submitted."""

    permission_classes = [permissions.IsAuthenticated, IsAlumni]

    @extend_schema(responses={200: AlumniSurveyResponseSerializer})
    def get(self, request):
        """The caller's submitted response. 404 if they haven't submitted
        yet."""
        try:
            survey = request.user.alumni_survey
        except AlumniSurveyResponse.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(AlumniSurveyResponseSerializer(survey).data)

    @extend_schema(
        request=AlumniSurveyResponseSerializer,
        responses={201: AlumniSurveyResponseSerializer},
    )
    def post(self, request):
        """Submit the survey. Every field is required. 400 if the caller
        already submitted one."""
        if AlumniSurveyResponse.objects.filter(user=request.user).exists():
            return Response(ALREADY_SUBMITTED, status=status.HTTP_400_BAD_REQUEST)

        serializer = AlumniSurveyResponseSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        try:
            # atomic: a failed insert mustn't break an enclosing transaction.
            with transaction.atomic():
                survey = serializer.save()
        except IntegrityError:
            # Lost a race with a concurrent submission by the same user.
            return Response(ALREADY_SUBMITTED, status=status.HTTP_400_BAD_REQUEST)
        return Response(AlumniSurveyResponseSerializer(survey).data, status=status.HTTP_201_CREATED)
