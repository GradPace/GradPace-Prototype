import json
from datetime import datetime

import pytest

from accounts.factories import (
    AdminUserFactory,
    AlumniUserFactory,
    StudentProfileFactory,
    UserFactory,
)
from accounts.tests.helpers import login
from intelligence.data_health import MAX_UNRECOGNIZED
from intelligence.factories import JobFactory, JobPostingFactory, JobSkillFactory

URL = '/api/intelligence/admin/data-health/'


def get_report(client, user=None):
    tokens = login(client, user or AdminUserFactory())
    return client.get(URL, HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}')


def occupation(body, soc_code):
    return next(row for row in body['occupations'] if row['soc_code'] == soc_code)


def healthy_job(soc_code, **kwargs):
    """3 postings, a wage and 2 skills - no flags."""
    job = JobFactory(soc_code=soc_code, **{'median_annual_wage': 100000, **kwargs})
    JobSkillFactory.create_batch(2, job=job)
    JobPostingFactory.create_batch(3, job=job)
    return job


def students_in(*locations):
    return [StudentProfileFactory(location=location) for location in locations]


# Who can see it
@pytest.mark.django_db
def test_requires_authentication(client):
    assert client.get(URL).status_code == 401


@pytest.mark.django_db
@pytest.mark.parametrize('factory', [UserFactory, AlumniUserFactory])
def test_non_admins_are_forbidden(client, factory):
    assert get_report(client, factory()).status_code == 403


# Catalog totals
@pytest.mark.django_db
def test_totals_split_by_source(client):
    healthy_job('15-1252')
    healthy_job('15-2051')
    generated = JobFactory(soc_code='15-1299', source='generated')
    JobSkillFactory(job=generated)

    body = get_report(client).json()

    assert body['totals'] == {
        'jobs': {'total': 3, 'official': 2, 'generated': 1},
        'skills': {'total': 5},
        'postings': {'total': 6, 'generated': 6},
    }


@pytest.mark.django_db
def test_empty_catalog(client):
    body = get_report(client).json()

    assert body['totals']['jobs'] == {'total': 0, 'official': 0, 'generated': 0}
    assert body['occupations'] == []
    assert body['catalog_updated_at'] is None


@pytest.mark.django_db
def test_catalog_updated_at_is_the_latest_row(client):
    job = healthy_job('15-1252')
    posting = job.postings.first()
    posting.save()  # the most recent write
    posting.refresh_from_db()

    body = get_report(client).json()

    assert datetime.fromisoformat(body['catalog_updated_at']) == posting.updated_at


# Per occupation
@pytest.mark.django_db
def test_occupation_counts(client):
    healthy_job('15-1252', title='Software Developers')

    row = occupation(get_report(client).json(), '15-1252')

    assert row == {
        'soc_code': '15-1252',
        'title': 'Software Developers',
        'source': 'official',
        'posting_count': 3,
        'skill_count': 2,
        'median_annual_wage': 100000,
        'few_postings': False,
        'missing_wage': False,
        'no_skills': False,
    }


@pytest.mark.django_db
def test_few_postings_flag(client):
    job = JobFactory(soc_code='15-1252', median_annual_wage=100000)
    JobSkillFactory(job=job)
    JobPostingFactory.create_batch(2, job=job)

    row = occupation(get_report(client).json(), '15-1252')

    assert row['posting_count'] == 2
    assert row['few_postings'] is True
    assert row['missing_wage'] is False
    assert row['no_skills'] is False


@pytest.mark.django_db
def test_missing_wage_flag(client):
    healthy_job('15-1252', median_annual_wage=None)

    row = occupation(get_report(client).json(), '15-1252')

    assert row['median_annual_wage'] is None
    assert row['missing_wage'] is True
    assert row['few_postings'] is False


@pytest.mark.django_db
def test_no_skills_flag(client):
    job = JobFactory(soc_code='15-1252', median_annual_wage=100000)
    JobPostingFactory.create_batch(3, job=job)

    row = occupation(get_report(client).json(), '15-1252')

    assert row['skill_count'] == 0
    assert row['no_skills'] is True
    assert row['few_postings'] is False


# Student locations
@pytest.mark.django_db
def test_location_counts(client):
    students_in('Norfolk, VA', '  Narfolk ', 'Narfolk', 'Nowhere, ZZ', '')

    locations = get_report(client).json()['student_locations']

    assert locations == {
        'profiles': 5,
        'with_location': 4,
        'recognized': 1,
        'unrecognized': 3,
        'unrecognized_values': [
            {'location': 'Narfolk', 'count': 2},
            {'location': 'Nowhere, ZZ', 'count': 1},
        ],
    }


@pytest.mark.django_db
def test_unrecognized_values_are_capped(client):
    students_in(*[f'Nowhere {n}, ZZ' for n in range(MAX_UNRECOGNIZED + 1)])

    locations = get_report(client).json()['student_locations']

    assert locations['unrecognized'] == MAX_UNRECOGNIZED + 1
    assert len(locations['unrecognized_values']) == MAX_UNRECOGNIZED


@pytest.mark.django_db
def test_locations_contain_no_user_identifiers(client):
    profiles = students_in('Narfolk', 'Norfolk, VA')
    for profile in profiles:
        profile.user.first_name, profile.user.last_name = 'Ada', 'Lovelace'
        profile.user.save()

    locations = get_report(client).json()['student_locations']

    assert set(locations) == {
        'profiles',
        'with_location',
        'recognized',
        'unrecognized',
        'unrecognized_values',
    }
    assert all(set(row) == {'location', 'count'} for row in locations['unrecognized_values'])
    text = json.dumps(locations)
    for profile in profiles:
        for identifier in (
            profile.user.email,
            str(profile.user.id),
            str(profile.id),
            profile.student_id,
            'Ada',
            'Lovelace',
        ):
            assert identifier not in text
