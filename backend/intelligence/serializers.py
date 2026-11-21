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
