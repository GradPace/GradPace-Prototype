from typing import cast

from django.db.models import Count
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.models import StudentProfile
from intelligence.models import Job

from .relevance import rank_resources_by_relevance
from .algorithms import calculate_benchmark_score
from .best_fit import best_fit_jobs
from .catalog import label_for, skill_catalog
from .job_benchmark import build_job_benchmark, get_job
from .scoring import score_student
from .serializers import (
    BenchmarkRequestSerializer,
    BenchmarkResultSerializer,
    BestFitJobSerializer,
    CatalogSkillSerializer,
    JobBenchmarkSerializer,
    RoleListItemSerializer,
    StudentBenchmarkSerializer,
)


class SampleBenchmarkView(APIView):
    """Runs the algorithm on hardcoded sample data - a smoke test to check
    the endpoint is wired up."""

    @extend_schema(responses={200: BenchmarkResultSerializer})
    def get(self, request):
        sample_profile = {'skills': 80.0, 'experience': 70.0, 'networking': 50.0}
        sample_weights = {'skills': 0.40, 'experience': 0.40, 'networking': 0.20}

        return Response(calculate_benchmark_score(sample_profile, sample_weights))


class BenchmarkView(APIView):
    """Receives a student profile and dynamic weights, runs the benchmark
    algorithm, and returns the result."""

    @extend_schema(request=BenchmarkRequestSerializer, responses={200: BenchmarkResultSerializer})
    def post(self, request):
        serializer = BenchmarkRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        # DRF's stubs type validated_data as `dict | empty` since it's unset
        # before is_valid() - it's always a dict once that has passed.
        data = cast(dict, serializer.validated_data)

        result = calculate_benchmark_score(data['student_profile'], data['dynamic_weights'])
        return Response(result)


class RoleListView(APIView):
    """Lists the jobs a student can be benchmarked against (from the
    intelligence app's BLS/O*NET data) - for the frontend's role picker."""

    @extend_schema(responses={200: RoleListItemSerializer(many=True)})
    def get(self, request):
        jobs = (
            Job.objects.filter(area='National')
            .annotate(posting_count=Count('postings'))
            .order_by('title')
        )
        return Response(
            [
                {'soc_code': job.soc_code, 'title': job.title, 'posting_count': job.posting_count}
                for job in jobs
            ]
        )


class JobBenchmarkView(APIView):
    """The benchmark for one job: the skills its postings ask for, with each
    skill's weight. What a student's readiness score is measured against."""

    @extend_schema(responses={200: JobBenchmarkSerializer})
    def get(self, request, soc_code):
        job = get_job(soc_code)
        if job is None:
            return Response(status=status.HTTP_404_NOT_FOUND)

        benchmark = build_job_benchmark(job)
        return Response(
            {
                'role': {'soc_code': job.soc_code, 'title': job.title},
                'postings_used': benchmark.postings_used,
                'seniorities_used': benchmark.seniorities_used,
                'skills': [
                    {
                        'name': skill.name,
                        'label': label_for(skill.name),
                        'skill_type': skill.skill_type,
                        'weight': skill.weight,
                    }
                    for skill in benchmark.skills
                ],
            }
        )


class SkillCatalogView(APIView):
    """The skills a student can pick from - every skill in at least one
    job's benchmark, or with ?role= just that job's. Save `name` (not
    `label`) on the student's Skill row. 400 if ?role= is unknown."""

    @extend_schema(
        parameters=[
            OpenApiParameter(
                'role',
                str,
                required=False,
                description="SOC code, e.g. 15-1252 - only that job's benchmark skills.",
            )
        ],
        responses={200: CatalogSkillSerializer(many=True)},
    )
    def get(self, request):
        soc_code = request.query_params.get('role')
        if soc_code is None:
            return Response(skill_catalog())

        job = get_job(soc_code)
        if job is None:
            return Response(
                {'role': [f'Unknown role {soc_code!r}.']}, status=status.HTTP_400_BAD_REQUEST
            )
        return Response(skill_catalog(jobs=[job]))


class MyBenchmarkView(APIView):
    """Scores the logged-in student's skills against a job's benchmark.

    Uses ?role= if given, otherwise the student's saved target_job. When the
    job scored is the target job, the overall score is also saved to
    StudentProfile.readiness_score (so looking at another role with ?role=
    never overwrites it) - `saved_to_profile` says which happened.

    404 if the caller has no student profile yet. 400 if ?role= isn't a
    known SOC code, or there's no ?role= and no target job saved."""

    @extend_schema(
        parameters=[
            OpenApiParameter(
                'role',
                str,
                required=False,
                description="SOC code, e.g. 15-1252. Defaults to the profile's target_job.",
            )
        ],
        responses={200: StudentBenchmarkSerializer},
    )
    def get(self, request):
        try:
            profile = request.user.student_profile
        except StudentProfile.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        soc_code = request.query_params.get('role')
        if soc_code is not None:
            job = get_job(soc_code)
            if job is None:
                return Response(
                    {'role': [f'Unknown role {soc_code!r}.']}, status=status.HTTP_400_BAD_REQUEST
                )
        elif profile.target_job is not None:
            job = profile.target_job
        else:
            return Response(
                {'role': ['No target job saved on the profile - pass ?role= or set one.']},
                status=status.HTTP_400_BAD_REQUEST,
            )

        result = score_student(profile, job)
        result['role'] = {'soc_code': job.soc_code, 'title': job.title}

        is_target = job.pk == profile.target_job_id
        if is_target:
            profile.readiness_score = result['overall_readiness_score']
            profile.save(update_fields=['readiness_score', 'updated_at'])
        result['saved_to_profile'] = is_target

        return Response(result)


class BestFitJobsView(APIView):
    """The logged-in student's readiness for every job, best match first -
    "you're closest to being ready for...". Jobs whose benchmark comes from
    under 10 postings are flagged limited_data and ranked after the rest.
    Doesn't change readiness_score. 404 if the caller has no student profile."""

    @extend_schema(responses={200: BestFitJobSerializer(many=True)})
    def get(self, request):
        try:
            profile = request.user.student_profile
        except StudentProfile.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)
        return Response(best_fit_jobs(profile))

class GapRelevanceView(APIView):
    """Scores and ranks catalog or learning resources against the logged-in 
    student's skill gap profile for a target job."""

    @extend_schema(
        parameters=[
            OpenApiParameter(
                'role',
                str,
                required=False,
                description="SOC code, e.g. 15-1252. Defaults to the profile's target_job.",
            )
        ]
    )
    def get(self, request):
        try:
            profile = request.user.student_profile
        except StudentProfile.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        soc_code = request.query_params.get('role')
        if soc_code is not None:
            job = get_job(soc_code)
            if job is None:
                return Response(
                    {'role': [f'Unknown role {soc_code!r}.']}, status=status.HTTP_400_BAD_REQUEST
                )
        elif profile.target_job is not None:
            job = profile.target_job
        else:
            return Response(
                {'role': ['No target job saved on the profile - pass ?role= or set one.']},
                status=status.HTTP_400_BAD_REQUEST,
            )

        benchmark = build_job_benchmark(job)

        # Sample catalog list (Replace with a database query if you have a catalog model)
        sample_catalog = [
            {'id': 1, 'title': 'SQL Mastery & Queries', 'skills': ['Structured query language SQL']},
            {'id': 2, 'title': 'Python for Data Analysis', 'skills': ['Python']},
            {'id': 3, 'title': 'Git & Version Control Essentials', 'skills': ['Git']},
        ]

        ranked_catalog = rank_resources_by_relevance(
            resources=sample_catalog,
            student_skills={s.name: s.proficiency_level for s in profile.skills.all()},
            benchmark_skills=benchmark.skills,
        )

        return Response({
            'role': {'soc_code': job.soc_code, 'title': job.title},
            'recommendations': ranked_catalog,
        })