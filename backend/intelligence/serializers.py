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
    location = serializers.CharField()
    focus = serializers.CharField()
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


class EventChatSerializer(serializers.Serializer):
    exchanges = ChatExchangeSerializer(many=True)
    chats_remaining = serializers.IntegerField()
    max_chats = serializers.IntegerField()


class EventChatRequestSerializer(serializers.Serializer):
    question = serializers.CharField(max_length=300, trim_whitespace=True)
