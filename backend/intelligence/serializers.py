from rest_framework import serializers


class EventSuggestionSerializer(serializers.Serializer):
    event = serializers.CharField()
    reason = serializers.CharField()


class EventSuggestionsSerializer(serializers.Serializer):
    suggestions = EventSuggestionSerializer(many=True)


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
