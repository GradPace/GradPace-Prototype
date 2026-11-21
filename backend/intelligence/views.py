import json

from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from . import places
from .llm import LLMUnavailable, chat_json
from .serializers import EventSuggestionsSerializer, PlaceSerializer

SAMPLE_STUDENT = {
    'major': 'Computer Science',
    'year': 'junior',
    'skills': ['Python', 'Git'],
    'goal': 'a software engineering internship',
}

SAMPLE_MESSAGES = [
    {
        'role': 'system',
        'content': (
            'You are a career advisor for university students. Suggest events a '
            'student should attend - career fairs, workshops, hackathons, info '
            'sessions, networking nights - to close the gaps between their '
            'profile and their goal. Answer in JSON only.'
        ),
    },
    {
        'role': 'user',
        'content': (
            f'Student profile: {json.dumps(SAMPLE_STUDENT)}\n'
            'Suggest 3 events, each with a one-sentence reason.'
        ),
    },
]

EVENT_SUGGESTIONS_SCHEMA = {
    'type': 'object',
    'properties': {
        'suggestions': {
            'type': 'array',
            'minItems': 1,
            'maxItems': 5,
            'items': {
                'type': 'object',
                'properties': {
                    'event': {'type': 'string'},
                    'reason': {'type': 'string'},
                },
                'required': ['event', 'reason'],
            },
        },
    },
    'required': ['suggestions'],
}

UNAVAILABLE = {'detail': 'The AI model is unavailable right now. Please try again shortly.'}


class SampleEventSuggestionsView(APIView):
    """Suggests events for a hardcoded sample student - a smoke test to check
    the backend can reach llama-server and get structured JSON back."""

    # The model serves one request at a time on CPU - per-user rate in
    # REST_FRAMEWORK's DEFAULT_THROTTLE_RATES['llm'].
    throttle_scope = 'llm'

    @extend_schema(
        responses={
            200: EventSuggestionsSerializer,
            503: OpenApiResponse(description='The model is unreachable or gave an unusable reply.'),
        }
    )
    def get(self, request):
        try:
            reply = chat_json(SAMPLE_MESSAGES, schema=EVENT_SUGGESTIONS_SCHEMA)
        except LLMUnavailable:
            return Response(UNAVAILABLE, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        # The schema constrains generation, but never pass model output
        # through unchecked.
        serializer = EventSuggestionsSerializer(data=reply)
        if not serializer.is_valid():
            return Response(UNAVAILABLE, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        return Response(serializer.validated_data)


PLACE_RESULTS = 8
MAX_PLACE_QUERY_CHARS = 100


class PlaceSearchView(APIView):
    """Autocomplete for the profile's location: US places whose name starts
    with ?q= (at least 2 letters), biggest first - at most 8. "nor" and
    "norfolk, v" both work; after a comma it narrows by state. Save the chosen
    `label` ("Norfolk, VA") as the location, so it can be found exactly."""

    @extend_schema(
        parameters=[
            OpenApiParameter('q', str, required=True, description="What's been typed so far.")
        ],
        responses={200: PlaceSerializer(many=True)},
    )
    def get(self, request):
        query = request.query_params.get('q', '')[:MAX_PLACE_QUERY_CHARS]
        return Response(
            [
                {'label': place.label, 'name': place.name, 'state': place.state}
                for place in places.search(query, limit=PLACE_RESULTS)
            ]
        )
