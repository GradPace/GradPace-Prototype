"""Event recommendations (prototype): the mock events in data/events.json,
narrowed to Hampton Roads, ranked for a student by skill-gap fit, date and
distance. The ranking is plain code; the LLM only picks among the top few
candidates and explains the pick (views.py), so it can't invent an event.

    events.json ─> load_events() ─> rank_events(student gaps, location, today)
                   (Hampton Roads)   skill fit 50% / date 25% / distance 25%
"""

import json
import math
import re
from datetime import date
from functools import lru_cache
from pathlib import Path

from django.utils.text import slugify

EVENTS_PATH = Path(__file__).parent / 'data' / 'events.json'

# The prototype only covers Hampton Roads: event cities not listed here are
# dropped (Richmond, Petersburg, the NC towns, ...). Approximate city-center
# (lat, lon) - enough for a "how far is it" score without a geocoding service.
HAMPTON_ROADS_CITIES = {
    'norfolk': (36.8508, -76.2859),
    'virginia beach': (36.8529, -75.9780),
    'chesapeake': (36.7682, -76.2875),
    'portsmouth': (36.8354, -76.2983),
    'suffolk': (36.7282, -76.5836),
    'hampton': (37.0299, -76.3452),
    'newport news': (37.0871, -76.4730),
    'williamsburg': (37.2707, -76.7075),
    'yorktown': (37.2388, -76.5097),
    'smithfield': (36.9824, -76.6310),
    'gloucester': (37.4135, -76.5246),
    'franklin': (36.6776, -76.9224),
}

WEIGHT_SKILLS = 0.50
WEIGHT_DATE = 0.25
WEIGHT_DISTANCE = 0.25

# Distance and date scores fall off linearly to 0 at these limits.
FAR_MILES = 60.0
FAR_DAYS = 90
# Used when the student's location isn't a known Hampton Roads city.
NEUTRAL_DISTANCE_SCORE = 0.5

_STOPWORDS = frozenset(
    'and or the of to a an in for with using use on at by as is are be from into '
    'systems system application applications'.split()
)


def _city_of(location):
    """'Norfolk, VA' -> 'norfolk'. Only the part before the comma."""
    return location.split(',')[0].strip().casefold()


@lru_cache(maxsize=1)
def _all_events():
    with EVENTS_PATH.open(encoding='utf-8') as events_file:
        raw = json.load(events_file)
    events = []
    for event in raw:
        city = _city_of(event['location'])
        if city not in HAMPTON_ROADS_CITIES:
            continue
        events.append({**event, 'id': slugify(event['title']), 'city': city})
    return events


def load_events():
    """Every Hampton Roads event, in file (date) order. Each is the JSON
    object plus `id` (slug of the title) and `city` (lowercase)."""
    return [dict(event) for event in _all_events()]


def get_event(event_id):
    return next((e for e in load_events() if e['id'] == event_id), None)


def upcoming_events(today):
    return [e for e in load_events() if date.fromisoformat(e['date']) >= today]


def student_city(location):
    """The Hampton Roads city named in a student's free-text location, or
    None. Longest name wins ('newport news' over any shorter match)."""
    text = (location or '').casefold()
    matches = [city for city in HAMPTON_ROADS_CITIES if re.search(rf'\b{city}\b', text)]
    return max(matches, key=len, default=None)


def miles_between(city_a, city_b):
    """Great-circle distance between two Hampton Roads cities, in miles."""
    lat1, lon1 = map(math.radians, HAMPTON_ROADS_CITIES[city_a])
    lat2, lon2 = map(math.radians, HAMPTON_ROADS_CITIES[city_b])
    a = (
        math.sin((lat2 - lat1) / 2) ** 2
        + math.cos(lat1) * math.cos(lat2) * math.sin((lon2 - lon1) / 2) ** 2
    )
    return 3958.8 * 2 * math.asin(math.sqrt(a))


def _words(text):
    """Lowercase word set, minus filler, with a trailing plural 's' dropped
    so 'databases' matches 'database'."""
    found = set()
    for word in re.findall(r'[a-z0-9+#]+', text.casefold()):
        if word in _STOPWORDS:
            continue
        found.add(word[:-1] if len(word) > 3 and word.endswith('s') else word)
    return found


def skill_fit(event, gaps):
    """0-1: how much of the student's skill gap the event's focus and topics
    touch. gaps: [{'label': 'SQL', 'weight': 0.35}, ...] - weight is how much
    room to grow the skill has. A gap counts once if any of its words appear
    in the event text; the score is the share of total gap weight covered."""
    total = sum(g['weight'] for g in gaps)
    if not total:
        return 0.0
    event_words = _words(' '.join([event['title'], event['focus'], *event['key_topics']]))
    covered = sum(g['weight'] for g in gaps if _words(g['label']) & event_words)
    return covered / total


def date_score(event, today):
    days = (date.fromisoformat(event['date']) - today).days
    return max(0.0, 1.0 - max(days, 0) / FAR_DAYS)


def distance_miles(event, location):
    """Miles from the student's city to the event, or None if their location
    isn't a known Hampton Roads city."""
    home = student_city(location)
    if home is None:
        return None
    return miles_between(home, event['city'])


def rank_events(gaps, location, today):
    """Upcoming Hampton Roads events, best first. Each is the event plus
    `score` (0-1), `distance_miles` (or None) and `skill_fit`. Ties go to the
    sooner event."""
    ranked = []
    for event in upcoming_events(today):
        fit = skill_fit(event, gaps)
        miles = distance_miles(event, location)
        distance = (
            NEUTRAL_DISTANCE_SCORE if miles is None else max(0.0, 1.0 - miles / FAR_MILES)
        )
        score = (
            WEIGHT_SKILLS * fit
            + WEIGHT_DATE * date_score(event, today)
            + WEIGHT_DISTANCE * distance
        )
        ranked.append(
            {
                **event,
                'score': round(score, 4),
                'skill_fit': round(fit, 4),
                'distance_miles': None if miles is None else round(miles, 1),
            }
        )
    ranked.sort(key=lambda e: (-e['score'], e['date']))
    return ranked


def student_gaps(profile, limit=8):
    """The student's biggest skill gaps for their target job, as
    [{'label': 'SQL', 'weight': room_to_grow}, ...] best first - the input
    skill_fit() wants. Empty if they haven't picked a target job."""
    # Imported here: benchmarks imports intelligence.models at load time.
    from benchmarks.scoring import room_to_grow, score_student

    if profile.target_job is None:
        return []
    result = score_student(profile, profile.target_job)
    gaps = {}
    for flagged in result['flagged_gaps']:
        for skill in flagged['top_unmet_skills']:
            gaps[skill['label']] = max(gaps.get(skill['label'], 0.0), room_to_grow(skill))
    ranked = sorted(gaps.items(), key=lambda item: (-item[1], item[0]))
    return [{'label': label, 'weight': round(weight, 4)} for label, weight in ranked[:limit]]
