from rest_framework import serializers


class BenchmarkRequestSerializer(serializers.Serializer):
    """Input for calculate_benchmark_score - both dicts are keyed by dimension
    name, e.g. {'skills': 75.0, 'experience': 60.0}."""

    student_profile = serializers.DictField(child=serializers.FloatField(), default=dict)
    dynamic_weights = serializers.DictField(child=serializers.FloatField(), default=dict)


class GapSerializer(serializers.Serializer):
    current = serializers.FloatField()
    weight = serializers.FloatField()
    gap = serializers.FloatField()


class BenchmarkResultSerializer(serializers.Serializer):
    overall_readiness_score = serializers.FloatField()
    gap_breakdown = serializers.DictField(child=GapSerializer())
