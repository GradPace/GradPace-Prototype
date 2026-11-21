"""Plain facts about an event - date, place, cost... - answered straight from
the event data, with no model. The model is only for open questions ("what will
I learn?"), where a slightly loose answer does little harm; a made-up price or
venue would.

    "Is it free and where is it?"  ->  matches cost + where  ->  answered here
    "Why is this one good for me?" ->  open-ended word       ->  model
"""

import re
from datetime import date

# A question with any of these is asking for more than a lookup, so it goes to
# the model even if it also mentions a fact ("is it free and what will I learn?").
OPEN_ENDED = re.compile(
    r'\b(learn|topics?|cover|covers|why|worth|help|helps|gaps?|recommend\w*|about|agenda|'
    r'schedule|explain|tell me|should|good for|fit|compare|better)\b'
)

# (name, pattern) - a question can match several.
RULES = [
    ('when', re.compile(r'\b(when|what (day|date|time)|starts?|starting|date|time)\b')),
    ('where', re.compile(r'\b(where|location|address|venue|directions?|located|city)\b')),
    ('cost', re.compile(r'\b(cost|costs|price|fee|free|tickets?|pay|how much)\b')),
    ('duration', re.compile(r'\b(how long|duration|ends?|finish)\b')),
    (
        'speakers',
        re.compile(r'\b(speakers?|presenters?|who\b.*\b(speaking|presenting|teaching))\b'),
    ),
    (
        'registration',
        re.compile(r'\b(register|registration|sign ?up|rsvp|enroll|seats?|capacity|spots?)\b'),
    ),
    (
        'prerequisites',
        re.compile(
            r'\b(prerequisites?|prereqs?|requirements?|experience|beginners?|audience|'
            r'who is it for|need to know)\b'
        ),
    ),
    ('format', re.compile(r'\b(in[- ]person|online|virtual|remote|hybrid|format)\b')),
]


def _long_date(iso):
    day = date.fromisoformat(iso)
    return f'{day:%A}, {day:%B} {day.day}, {day.year}'


def _where(event):
    if event['venue'] == 'TBA':
        return f"It's in {event['location']}; the venue is TBA."
    return f"It's in {event['location']}, at {event['venue']}."


ANSWERS = {
    'when': lambda e: f"It's on {_long_date(e['date'])} at {e['time']}.",
    'where': _where,
    'cost': lambda e: f'Cost: {e["cost"]}.',
    'duration': lambda e: f'It runs about {e["duration"]}.',
    'speakers': lambda e: f'Speakers: {e["speakers"]}.',
    'registration': lambda e: f'Registration: {e["registration"]}.',
    'prerequisites': lambda e: f'Prerequisites: {e["prerequisites"]}. Meant for: {e["audience"]}.',
    'format': lambda e: f'Format: {e["format"]}.',
}


def answer(question, event):
    """The event data's answer to a plain-facts question, or None if the
    question is open-ended or isn't about any fact we hold."""
    text = question.casefold()
    if OPEN_ENDED.search(text):
        return None
    matched = [name for name, pattern in RULES if pattern.search(text)]
    if not matched:
        return None
    return ' '.join(ANSWERS[name](event) for name in matched)
