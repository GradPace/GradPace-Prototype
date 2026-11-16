from rest_framework import serializers


class EventSuggestionSerializer(serializers.Serializer):
    event = serializers.CharField()
    reason = serializers.CharField()


class EventSuggestionsSerializer(serializers.Serializer):
    suggestions = EventSuggestionSerializer(many=True)
