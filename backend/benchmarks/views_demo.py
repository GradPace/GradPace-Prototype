"""Demo endpoints (GP-82) - demo version of views.py, for ODU students
targeting Software Developers in Norfolk. See scoring_demo.py for the score.

Neither endpoint writes anything: the demo score is never saved to
StudentProfile.readiness_score, so the original benchmark is unaffected."""

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import StudentProfile

from .job_benchmark_demo import LOCATION, SCHOOL, build_job_benchmark_demo, get_demo_job
from .scoring_demo import CERTIFICATES, COURSES, LEVELS, score_skills, score_student_demo
from .serializers_demo import DemoOptionsSerializer, StudentBenchmarkDemoSerializer

NO_JOB_DATA = {'detail': 'Software Developers job data is missing - run migrate.'}


class DemoOptionsView(APIView):
    """What the demo input page's pickers offer: skill levels, skill groups
    (with the tools in each and the points each group is worth), ODU
    courses and the certificates that earn a bonus."""

    @extend_schema(responses={200: DemoOptionsSerializer})
    def get(self, request):
        job = get_demo_job()
        if job is None:
            return Response(NO_JOB_DATA, status=status.HTTP_404_NOT_FOUND)

        # Scoring nobody's skills gives each group's points with none earned.
        _, groups = score_skills({}, build_job_benchmark_demo(job).groups)
        return Response(
            {
                'role': {'soc_code': job.soc_code, 'title': job.title},
                'school': SCHOOL,
                'location': LOCATION,
                'levels': [
                    {'value': value, 'label': label, 'credit': credit}
                    for value, (label, credit) in LEVELS.items()
                ],
                'skill_groups': [
                    {
                        'key': group['key'],
                        'name': group['name'],
                        'points': group['out_of'],
                        'tools': group['options'],
                    }
                    for group in groups
                ],
                'courses': [{'code': code, 'name': name} for code, name in COURSES],
                'certificates': CERTIFICATES,
            }
        )


class MyBenchmarkDemoView(APIView):
    """The logged-in student's demo readiness: skills + ODU courses +
    certificate bonus, scored against Norfolk Software Developer postings.
    404 if the caller has no student profile yet, or the job data is missing."""

    @extend_schema(responses={200: StudentBenchmarkDemoSerializer})
    def get(self, request):
        try:
            profile = request.user.student_profile
        except StudentProfile.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        job = get_demo_job()
        if job is None:
            return Response(NO_JOB_DATA, status=status.HTTP_404_NOT_FOUND)

        result = score_student_demo(profile, build_job_benchmark_demo(job))
        result['role'] = {'soc_code': job.soc_code, 'title': job.title}
        return Response(result)
