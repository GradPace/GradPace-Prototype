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


# Filler that doesn't need to appear in the cited field.
_FILLER = frozenset(
    {
        *('this', 'that', 'with', 'from', 'have', 'will', 'your', 'their', 'there', 'about'),
        *('which', 'what', 'when', 'where', 'these', 'those', 'they', 'them', 'event', 'also'),
        *('into', 'more', 'some', 'such', 'than', 'then', 'been', 'being', 'does', 'only'),
        *('over', 'just', 'very', 'can', 'could', 'would', 'should', 'must', 'may', 'might'),
        *('for', 'and', 'the', 'are', 'you', 'its', 'was', 'were', 'has', 'had', 'not', 'but'),
        *('all', 'any', 'each', 'other'),
    }
)


def _content_words(text):
    words = re.findall(r'[a-z0-9]+', text.casefold())
    # Drop a plural 's' so 'sessions' matches 'session'.
    return {w[:-1] if len(w) > 4 and w.endswith('s') else w for w in words if w not in _FILLER}


def grounded(answer, field_text):
    """True if the answer sticks to what the cited field says: every number in
    it appears in the field, and most of its other words do too. The question
    is deliberately not evidence: "is it 400 attendees?" mustn't let the model
    repeat 400. A model that names a real field but writes something invented fails
    this, and the caller falls back to "that isn't in the details"."""
    allowed = _content_words(field_text)
    words = [w for w in _content_words(answer) if len(w) > 2 or w.isdigit()]
    if not words:
        return False
    numbers = [w for w in words if any(ch.isdigit() for ch in w)]
    if any(n not in allowed for n in numbers):
        return False
    return sum(1 for w in words if w in allowed) / len(words) >= GROUNDED_SHARE


# Share of an answer's content words that must come from the cited field.
GROUNDED_SHARE = 0.6
