from rest_framework import serializers

from benchmarks.catalog import skill_catalog

from .models import AlumniSurveyResponse

MAX_SKILLS = 5


class AlumniSurveyResponseSerializer(serializers.ModelSerializer):
    """Every question is required and can't be blank (FR-3.1.1.6.2-03).
    `user` always comes from the caller, never from the request body."""

    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    current_job_title = serializers.CharField(max_length=150)
    top_skills = serializers.ListField(
        child=serializers.CharField(), min_length=1, max_length=MAX_SKILLS
    )
    preparedness_rating = serializers.IntegerField(min_value=1, max_value=5)
    platform_helpfulness_rating = serializers.IntegerField(min_value=1, max_value=5)
    suggested_skills = serializers.ListField(
        child=serializers.CharField(max_length=100), min_length=1, max_length=MAX_SKILLS
    )
    platform_feedback = serializers.CharField(max_length=2000)

    class Meta:
        model = AlumniSurveyResponse
        fields = [
            'id',
            'user',
            'current_job_title',
            'industry',
            'top_skills',
            'preparedness_rating',
            'platform_helpfulness_rating',
            'suggested_skills',
            'platform_feedback',
            'submitted_at',
        ]
        read_only_fields = ['id', 'submitted_at']

    def validate_top_skills(self, value):
        if len(set(value)) != len(value):
            raise serializers.ValidationError('Each skill can only be listed once.')
        catalog_names = {skill['name'] for skill in skill_catalog()}
        unknown = sorted(name for name in value if name not in catalog_names)
        if unknown:
            raise serializers.ValidationError(
                f'Not in the skill catalog: {", ".join(unknown)}. '
                'Use a `name` from /api/benchmark/skills/.'
            )
        return value

    def validate_suggested_skills(self, value):
        # CharField has already stripped each item and rejected blank ones.
        if len({skill.lower() for skill in value}) != len(value):
            raise serializers.ValidationError('Each skill can only be listed once.')
        return value
