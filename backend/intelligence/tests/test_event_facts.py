"""Plain-fact lookups (intelligence/event_facts.py) - no database, no model."""

import pytest

from .. import event_facts, events


@pytest.fixture
def event():
    return events.get_event('datacore-database-engineering-conference')


def test_every_event_has_every_field_the_chat_can_answer_from():
    for event in events.load_events():
        for field in events.FIELD_LABELS:
            assert event.get(field), f'{event["title"]} is missing {field}'


@pytest.mark.parametrize(
    ('question', 'expected'),
    [
        ('When is it?', 'Saturday, December 19, 2026 at 1:30 PM EST'),
        ('what time does it start', '1:30 PM EST'),
        ('Where is this?', 'Yorktown Waterfront Conference Center'),
        ('Is it free?', 'Cost: Free.'),
        ('How much does it cost', 'Cost: Free.'),
        ('How long is it?', 'about 5 hours'),
        ('Who is speaking?', 'Speakers: TBA.'),
        ('How do I sign up?', 'Registration: Free online registration; capacity 80.'),
        ('Any prerequisites?', 'An intro database course or equivalent'),
        ('Is it online?', 'Format: In person.'),
    ],
)
def test_plain_fact_questions_are_answered_from_the_event(event, question, expected):
    assert expected in event_facts.answer(question, event)


def test_a_question_about_several_facts_gets_each_answer(event):
    reply = event_facts.answer('Where is it and is it free?', event)

    assert 'Yorktown Waterfront Conference Center' in reply
    assert 'Cost: Free.' in reply


@pytest.mark.parametrize(
    'question',
    [
        'What will I learn?',
        'Why is this one good for me?',
        'Is it free and what will I learn?',
        'Is it worth it?',
        'Is lunch provided?',  # a fact we don't hold - the model says so
        'hello',
    ],
)
def test_open_ended_or_unknown_questions_are_left_to_the_model(event, question):
    assert event_facts.answer(question, event) is None


def test_a_tba_venue_is_reported_as_tba(event):
    event = {**event, 'venue': 'TBA'}

    assert event_facts.answer('Where?', event) == "It's in Yorktown, VA; the venue is TBA."
