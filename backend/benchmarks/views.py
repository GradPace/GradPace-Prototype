from typing import cast

from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from .algorithms import calculate_benchmark_score
from .serializers import BenchmarkRequestSerializer, BenchmarkResultSerializer


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
