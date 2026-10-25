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


class JobSkillResultSerializer(serializers.Serializer):
    name = serializers.CharField(help_text='Exact O*NET name')
    label = serializers.CharField(help_text='Display name, e.g. "SQL"')
    demand = serializers.FloatField(help_text="Share of the job's postings listing it, 0-1")
    your_level = serializers.IntegerField(
        allow_null=True,
        help_text='Proficiency 1-4 (beginner-expert); null = not on your profile',
    )
    met = serializers.BooleanField()


class FlaggedGapSerializer(serializers.Serializer):
    dimension = serializers.CharField()
    gap = serializers.FloatField()
    points_available = serializers.FloatField()
    top_unmet_skills = JobSkillResultSerializer(many=True)


class RoleSerializer(serializers.Serializer):
    soc_code = serializers.CharField()
    title = serializers.CharField()


class RoleListItemSerializer(RoleSerializer):
    posting_count = serializers.IntegerField(help_text="How many postings the job's data has")


class BenchmarkInfoSerializer(serializers.Serializer):
    postings_used = serializers.IntegerField(
        help_text='How many postings the benchmark is built from'
    )
    seniorities_used = serializers.CharField(help_text="'intern/entry', 'all' or 'none'")


class StudentBenchmarkSerializer(BenchmarkResultSerializer):
    """BenchmarkResultSerializer plus the job it was scored against, every
    in-demand skill per dimension, and the gaps ranked by impact."""

    role = RoleSerializer()
    benchmark = BenchmarkInfoSerializer()
    saved_to_profile = serializers.BooleanField(
        help_text="True if this was the student's target job, so readiness_score was updated"
    )
    skills = serializers.DictField(child=JobSkillResultSerializer(many=True))
    flagged_gaps = FlaggedGapSerializer(many=True)


class BestFitJobSerializer(serializers.Serializer):
    role = RoleSerializer()
    overall_readiness_score = serializers.FloatField()
    postings_used = serializers.IntegerField()
    limited_data = serializers.BooleanField(
        help_text='Benchmark built from under 10 postings - show with a caveat'
    )
    top_unmet_skills = JobSkillResultSerializer(many=True)


class BenchmarkSkillSerializer(serializers.Serializer):
    name = serializers.CharField(help_text='Exact O*NET name')
    label = serializers.CharField()
    skill_type = serializers.CharField()
    weight = serializers.FloatField(help_text="Share of the job's postings listing it, 0-1")


class JobBenchmarkSerializer(serializers.Serializer):
    role = RoleSerializer()
    postings_used = serializers.IntegerField()
    seniorities_used = serializers.CharField(help_text="'intern/entry', 'all' or 'none'")
    skills = BenchmarkSkillSerializer(many=True)


class CatalogSkillSerializer(serializers.Serializer):
    name = serializers.CharField(help_text='Exact O*NET name - save this on the Skill row')
    label = serializers.CharField(help_text='Display name')
    skill_type = serializers.CharField()
    job_count = serializers.IntegerField(help_text="How many jobs' benchmarks include it")
    demand = serializers.FloatField(help_text='Its highest weight in any of those benchmarks, 0-1')
