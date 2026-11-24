from rest_framework import serializers


class EventSuggestionSerializer(serializers.Serializer):
    event = serializers.CharField()
    reason = serializers.CharField()


class EventSuggestionsSerializer(serializers.Serializer):
    suggestions = EventSuggestionSerializer(many=True)


class PlaceSerializer(serializers.Serializer):
    label = serializers.CharField(help_text="'Norfolk, VA' - save this as the profile's location.")
    name = serializers.CharField()
    state = serializers.CharField()


class EventSerializer(serializers.Serializer):
    id = serializers.CharField(help_text='Slug of the title - use it in the chat URL.')
    title = serializers.CharField()
    date = serializers.DateField()
    time = serializers.CharField()
    duration = serializers.CharField()
    location = serializers.CharField()
    venue = serializers.CharField()
    cost = serializers.CharField()
    format = serializers.CharField()
    focus = serializers.CharField()
    audience = serializers.CharField()
    prerequisites = serializers.CharField()
    registration = serializers.CharField()
    speakers = serializers.CharField()
    description = serializers.CharField()
    agenda = serializers.ListField(child=serializers.CharField())
    key_topics = serializers.ListField(child=serializers.CharField())


class EventRecommendationSerializer(serializers.Serializer):
    event = EventSerializer()
    reason = serializers.CharField()
    reason_source = serializers.ChoiceField(
        choices=['ai', 'fallback'],
        help_text="'fallback' = the model was unavailable, so the reason is "
        'a template built from the ranking.',
    )
    distance_miles = serializers.FloatField(allow_null=True)
    chats_remaining = serializers.IntegerField()


class ChatExchangeSerializer(serializers.Serializer):
    question = serializers.CharField()
    answer = serializers.CharField()
    source = serializers.ChoiceField(
        choices=['model', 'facts', 'unknown'],
        help_text="Only 'model' answers use up one of the student's questions.",
    )


class EventChatSerializer(serializers.Serializer):
    exchanges = ChatExchangeSerializer(many=True)
    chats_remaining = serializers.IntegerField()
    max_chats = serializers.IntegerField()


class EventChatRequestSerializer(serializers.Serializer):
    question = serializers.CharField(max_length=300, trim_whitespace=True)


# --- Admin data health -----------------------------------------------------


class SourceTotalsSerializer(serializers.Serializer):
    total = serializers.IntegerField()
    by_source = serializers.DictField(
        child=serializers.IntegerField(),
        help_text='Count per source value in the database (every model choice, even at 0), '
        "with 'unknown' for a blank source. Always adds up to total.",
    )


class SkillTotalsSerializer(serializers.Serializer):
    total = serializers.IntegerField()


class CatalogTotalsSerializer(serializers.Serializer):
    jobs = SourceTotalsSerializer()
    skills = SkillTotalsSerializer()
    postings = SourceTotalsSerializer()


class OccupationHealthSerializer(serializers.Serializer):
    soc_code = serializers.CharField()
    title = serializers.CharField()
    source = serializers.CharField()
    posting_count = serializers.IntegerField()
    skill_count = serializers.IntegerField()
    median_annual_wage = serializers.IntegerField(allow_null=True)
    few_postings = serializers.BooleanField(help_text='Fewer than 3 postings.')
    missing_wage = serializers.BooleanField()
    no_skills = serializers.BooleanField()


class UnrecognizedLocationSerializer(serializers.Serializer):
    location = serializers.CharField()
    count = serializers.IntegerField()


class StudentLocationsSerializer(serializers.Serializer):
    profiles = serializers.IntegerField()
    with_location = serializers.IntegerField()
    recognized = serializers.IntegerField(help_text='Locations places.lookup can place.')
    unrecognized = serializers.IntegerField()
    unrecognized_values = UnrecognizedLocationSerializer(
        many=True, help_text='Most common first, at most 20.'
    )


class DataHealthSerializer(serializers.Serializer):
    totals = CatalogTotalsSerializer()
    catalog_updated_at = serializers.DateTimeField(
        allow_null=True,
        help_text='Latest updated_at across jobs, skills and postings - when the catalog '
        'was last seeded or edited. Null when it is empty.',
    )
    occupations = OccupationHealthSerializer(many=True)
    student_locations = StudentLocationsSerializer()
