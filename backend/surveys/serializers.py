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


# --- Admin results (GP-98) --------------------------------------------------


class RatingCountSerializer(serializers.Serializer):
    value = serializers.IntegerField(min_value=1, max_value=5)
    count = serializers.IntegerField()


class RatingSummarySerializer(serializers.Serializer):
    average = serializers.FloatField(allow_null=True, help_text='Null when there are no responses.')
    distribution = RatingCountSerializer(many=True, help_text='Every value 1-5, even at 0.')


class RatingsSerializer(serializers.Serializer):
    preparedness_rating = RatingSummarySerializer(
        help_text='How prepared they felt for their first job.'
    )
    platform_helpfulness_rating = RatingSummarySerializer(
        help_text='How much GradPace helped them get there.'
    )


class IndustryResultSerializer(serializers.Serializer):
    code = serializers.CharField()
    label = serializers.CharField()
    count = serializers.IntegerField()
    preparedness_average = serializers.FloatField(
        allow_null=True, help_text='Null below 3 responses in this industry.'
    )
    platform_helpfulness_average = serializers.FloatField(
        allow_null=True, help_text='Null below 3 responses in this industry.'
    )


class TopSkillCountSerializer(serializers.Serializer):
    name = serializers.CharField(help_text='Skill catalog name.')
    label = serializers.CharField(help_text='What to show (benchmarks label_for).')
    count = serializers.IntegerField()


class SuggestedSkillCountSerializer(serializers.Serializer):
    skill = serializers.CharField(help_text='The most common spelling of the group.')
    count = serializers.IntegerField()


class FeedbackSerializer(serializers.Serializer):
    text = serializers.CharField()
    submitted_at = serializers.DateTimeField()


class SurveyResultsSerializer(serializers.Serializer):
    """Aggregates only - no names, emails, ids or job titles."""

    response_count = serializers.IntegerField()
    latest_submitted_at = serializers.DateTimeField(allow_null=True)
    ratings = RatingsSerializer()
    by_industry = IndustryResultSerializer(
        many=True,
        help_text='Every industry choice, in choice order, even at 0, then one '
        "'Unspecified' row (code '') for stored values that aren't a choice, if any.",
    )
    top_skills = TopSkillCountSerializer(
        many=True, help_text='Alumni per skill (a response counts a skill once). Most common first.'
    )
    suggested_skills = SuggestedSkillCountSerializer(
        many=True,
        help_text='Grouped ignoring case and surrounding spaces. Most common first, at most 20.',
    )
    feedback_count = serializers.IntegerField(help_text='All responses with feedback.')
    feedback = FeedbackSerializer(many=True, help_text='Newest first, at most 50.')
