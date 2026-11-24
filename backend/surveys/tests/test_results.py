import json
from datetime import UTC, datetime, timedelta

import pytest

from accounts.factories import AdminUserFactory, AlumniUserFactory, UserFactory
from accounts.tests.helpers import login
from benchmarks.catalog import label_for

from ..factories import AlumniSurveyResponseFactory
from ..models import AlumniSurveyResponse
from ..results import MAX_FEEDBACK, MAX_SUGGESTED_SKILLS, MIN_RESPONSES_FOR_AVERAGES

URL = '/api/survey/admin/results/'
AWS = 'Amazon Web Services AWS software'


def get_results(client, user=None):
    tokens = login(client, user or AdminUserFactory())
    return client.get(URL, HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')


def results(client):
    response = get_results(client)
    assert response.status_code == 200
    return response.json()


def counts(distribution):
    return [row['count'] for row in distribution]


def industry(body, code):
    return next(row for row in body['by_industry'] if row['code'] == code)


# Who can see it
@pytest.mark.django_db
def test_requires_authentication(client):
    assert client.get(URL).status_code == 401


@pytest.mark.django_db
@pytest.mark.parametrize('factory', [UserFactory, AlumniUserFactory])
def test_non_admins_are_forbidden(client, factory):
    assert get_results(client, factory()).status_code == 403


# Nothing submitted yet
@pytest.mark.django_db
def test_empty_database(client):
    body = results(client)

    assert body['response_count'] == 0
    assert body['latest_submitted_at'] is None
    for field in ('preparedness_rating', 'platform_helpfulness_rating'):
        assert body['ratings'][field] == {
            'average': None,
            'distribution': [{'value': value, 'count': 0} for value in range(1, 6)],
        }
    assert [row['code'] for row in body['by_industry']] == [
        code for code, _ in AlumniSurveyResponse.INDUSTRY_CHOICES
    ]
    assert all(
        row['count'] == 0
        and row['preparedness_average'] is None
        and row['platform_helpfulness_average'] is None
        for row in body['by_industry']
    )
    assert body['top_skills'] == []
    assert body['suggested_skills'] == []
    assert body['feedback_count'] == 0
    assert body['feedback'] == []


# Ratings
@pytest.mark.django_db
def test_rating_averages_and_distributions(client):
    for preparedness, helpfulness in [(1, 5), (4, 5), (4, 3), (5, 2)]:
        AlumniSurveyResponseFactory(
            preparedness_rating=preparedness, platform_helpfulness_rating=helpfulness
        )

    body = results(client)

    assert body['response_count'] == 4
    preparedness = body['ratings']['preparedness_rating']
    assert preparedness['average'] == 3.5
    assert counts(preparedness['distribution']) == [1, 0, 0, 2, 1]
    helpfulness = body['ratings']['platform_helpfulness_rating']
    assert helpfulness['average'] == 3.75
    assert counts(helpfulness['distribution']) == [0, 1, 1, 0, 2]


@pytest.mark.django_db
def test_latest_submitted_at(client):
    older, newer = AlumniSurveyResponseFactory(), AlumniSurveyResponseFactory()
    when = datetime(2026, 11, 20, 14, 0, tzinfo=UTC)
    AlumniSurveyResponse.objects.filter(pk=older.pk).update(submitted_at=when - timedelta(days=1))
    AlumniSurveyResponse.objects.filter(pk=newer.pk).update(submitted_at=when)

    body = results(client)

    assert datetime.fromisoformat(body['latest_submitted_at']) == when


# By industry
@pytest.mark.django_db
def test_industry_averages_need_enough_responses(client):
    assert MIN_RESPONSES_FOR_AVERAGES == 3
    for rating in (2, 4):
        AlumniSurveyResponseFactory(
            industry='finance', preparedness_rating=rating, platform_helpfulness_rating=rating
        )
    for preparedness, helpfulness in [(3, 4), (4, 4), (5, 5)]:
        AlumniSurveyResponseFactory(
            industry='software',
            preparedness_rating=preparedness,
            platform_helpfulness_rating=helpfulness,
        )

    body = results(client)

    assert industry(body, 'finance') == {
        'code': 'finance',
        'label': 'Finance / Banking',
        'count': 2,
        'preparedness_average': None,
        'platform_helpfulness_average': None,
    }
    software = industry(body, 'software')
    assert software['count'] == 3
    assert software['preparedness_average'] == 4.0
    assert software['platform_helpfulness_average'] == 4.33
    assert industry(body, 'healthcare')['count'] == 0


# Skills
@pytest.mark.django_db
def test_top_skills_use_catalog_labels_most_common_first(client):
    AlumniSurveyResponseFactory(top_skills=[AWS, 'Python'])
    AlumniSurveyResponseFactory(top_skills=[AWS])

    body = results(client)

    assert body['top_skills'] == [
        {'name': AWS, 'label': 'AWS', 'count': 2},
        {'name': 'Python', 'label': label_for('Python'), 'count': 1},
    ]
    assert label_for(AWS) == 'AWS'


@pytest.mark.django_db
def test_suggested_skills_group_case_and_spaces(client):
    AlumniSurveyResponseFactory(suggested_skills=['Rust', 'Go'])
    AlumniSurveyResponseFactory(suggested_skills=['rust'])
    AlumniSurveyResponseFactory(suggested_skills=[' Rust '])

    body = results(client)

    assert body['suggested_skills'] == [
        {'skill': 'Rust', 'count': 3},
        {'skill': 'Go', 'count': 1},
    ]


@pytest.mark.django_db
def test_suggested_skills_are_capped(client):
    for n in range(MAX_SUGGESTED_SKILLS + 1):
        AlumniSurveyResponseFactory(suggested_skills=[f'Skill {n:02d}'])

    body = results(client)

    assert len(body['suggested_skills']) == MAX_SUGGESTED_SKILLS


# Feedback
@pytest.mark.django_db
def test_feedback_is_newest_first_with_text_and_date_only(client):
    start = datetime(2026, 11, 1, tzinfo=UTC)
    for day, text in enumerate(['first', 'second', 'third']):
        response = AlumniSurveyResponseFactory(platform_feedback=text)
        AlumniSurveyResponse.objects.filter(pk=response.pk).update(
            submitted_at=start + timedelta(days=day)
        )

    body = results(client)

    assert [item['text'] for item in body['feedback']] == ['third', 'second', 'first']
    assert all(set(item) == {'text', 'submitted_at'} for item in body['feedback'])
    assert body['feedback_count'] == 3


@pytest.mark.django_db
def test_feedback_is_capped_but_counted(client):
    AlumniSurveyResponseFactory.create_batch(MAX_FEEDBACK + 1)

    body = results(client)

    assert len(body['feedback']) == MAX_FEEDBACK
    assert body['feedback_count'] == MAX_FEEDBACK + 1


# Privacy
@pytest.mark.django_db
def test_results_contain_no_user_identifiers(client):
    responses = [
        AlumniSurveyResponseFactory(
            user=AlumniUserFactory(
                email=f'zelda.quill{n}@example.com', first_name='Zelda', last_name='Quillfeather'
            ),
            current_job_title='Zebra Quantum Wrangler',
            industry='software',
        )
        for n in range(MIN_RESPONSES_FOR_AVERAGES)
    ]

    text = json.dumps(results(client))

    for response in responses:
        for identifier in (
            response.user.email,
            str(response.user.id),
            str(response.id),
            'Zelda',
            'Quillfeather',
            'Zebra Quantum Wrangler',
        ):
            assert identifier not in text
