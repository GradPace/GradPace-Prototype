import datetime

import pytest
from django.utils import timezone

from .. import roles
from ..factories import (
    AlumniProfileFactory,
    CertificateFactory,
    RoleFactory,
    SkillFactory,
    StudentProfileFactory,
    TakenClassFactory,
    UserFactory,
)
from ..models import AlumniProfile, Certificate, Skill, StudentProfile, TakenClass
from .helpers import login

URL = '/api/auth/convert-to-alumni/'
GRADUATION_DATE = '2025-05-10'


def convert(client, user, data=None):
    tokens = login(client, user)
    return client.post(
        URL,
        {'graduation_date': GRADUATION_DATE} if data is None else data,
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}',
    )


def role_of(user):
    user.refresh_from_db()
    return user.role.role_name if user.role else None


# Who can convert
@pytest.mark.django_db
def test_requires_authentication(client):
    response = client.post(
        URL, {'graduation_date': GRADUATION_DATE}, content_type='application/json'
    )

    assert response.status_code == 401


@pytest.mark.django_db
def test_alumni_cannot_convert_again(client):
    alum = AlumniProfileFactory(graduation_date=datetime.date(2024, 12, 15))

    response = convert(client, alum.user)

    assert response.status_code == 403
    alum.refresh_from_db()
    assert alum.graduation_date == datetime.date(2024, 12, 15)


@pytest.mark.django_db
@pytest.mark.parametrize('role', [roles.ADMIN, None])
def test_non_students_cannot_convert(client, role):
    user = UserFactory(role=RoleFactory(role_name=role) if role else None)
    StudentProfileFactory(user=user)

    response = convert(client, user)

    assert response.status_code == 403
    assert not AlumniProfile.objects.exists()


@pytest.mark.django_db
def test_requires_a_student_profile(client):
    student = UserFactory()

    response = convert(client, student)

    assert response.status_code == 404
    assert role_of(student) == roles.STUDENT
    assert not AlumniProfile.objects.exists()


# Graduation date
@pytest.mark.django_db
@pytest.mark.parametrize(
    'data',
    [
        {},
        {'graduation_date': ''},
        {'graduation_date': 'May 2025'},
        {'graduation_date': '1899-12-31'},
    ],
    ids=['missing', 'blank', 'bad-format', 'before-1900'],
)
def test_invalid_graduation_date_is_rejected(client, data):
    profile = StudentProfileFactory()

    response = convert(client, profile.user, data)

    assert response.status_code == 400
    assert 'graduation_date' in response.json()
    assert role_of(profile.user) == roles.STUDENT
    assert not AlumniProfile.objects.exists()


@pytest.mark.django_db
def test_future_graduation_date_is_rejected(client):
    profile = StudentProfileFactory()
    tomorrow = timezone.localdate() + datetime.timedelta(days=1)

    response = convert(client, profile.user, {'graduation_date': tomorrow.isoformat()})

    assert response.status_code == 400
    assert response.json() == {'graduation_date': ['Graduation date cannot be in the future.']}
    assert role_of(profile.user) == roles.STUDENT
    profile.refresh_from_db()
    assert profile.graduated is False


@pytest.mark.django_db
def test_graduating_today_is_allowed(client):
    profile = StudentProfileFactory()
    today = timezone.localdate()

    response = convert(client, profile.user, {'graduation_date': today.isoformat()})

    assert response.status_code == 200
    assert AlumniProfile.objects.get(user=profile.user).graduation_date == today


# Converting
@pytest.mark.django_db
def test_student_converts_to_alumni(client):
    profile = StudentProfileFactory()

    response = convert(client, profile.user)

    assert response.status_code == 200
    assert response.json() == {'role': roles.ALUMNI, 'graduation_date': GRADUATION_DATE}
    assert role_of(profile.user) == roles.ALUMNI
    profile.refresh_from_db()
    assert profile.graduated is True
    alumni_profile = AlumniProfile.objects.get(user=profile.user)
    assert alumni_profile.graduation_date == datetime.date(2025, 5, 10)


@pytest.mark.django_db
def test_profile_data_is_kept(client):
    profile = StudentProfileFactory(location='Norfolk, VA')
    TakenClassFactory(student=profile)
    SkillFactory(student=profile, name='Python')
    CertificateFactory(student=profile)
    before = StudentProfile.objects.values().get(pk=profile.pk)

    response = convert(client, profile.user)

    assert response.status_code == 200
    after = StudentProfile.objects.values().get(pk=profile.pk)
    changed = {key for key in before if before[key] != after[key]}
    assert changed == {'graduated', 'updated_at'}
    assert TakenClass.objects.filter(student=profile).count() == 1
    assert Skill.objects.filter(student=profile, name='Python').exists()
    assert Certificate.objects.filter(student=profile).count() == 1


@pytest.mark.django_db
def test_new_role_applies_without_logging_in_again(client):
    """JWT auth loads the user fresh on every request. The access token
    used to convert works as an alum straight away."""
    profile = StudentProfileFactory()
    tokens = login(client, profile.user)
    headers = {'HTTP_AUTHORIZATION': f'Bearer {tokens["access"]}'}

    client.post(
        URL, {'graduation_date': GRADUATION_DATE}, content_type='application/json', **headers
    )
    response = client.get('/api/auth/me/', **headers)

    assert response.json()['role'] == roles.ALUMNI


@pytest.mark.django_db
def test_existing_alumni_profile_is_reused(client):
    """An AlumniProfile made by hand in the admin (no date) gets the date,
    instead of a second one being created."""
    profile = StudentProfileFactory()
    existing = AlumniProfileFactory(user=profile.user, graduation_date=None)

    response = convert(client, profile.user)

    assert response.status_code == 200
    assert AlumniProfile.objects.filter(user=profile.user).count() == 1
    existing.refresh_from_db()
    assert existing.graduation_date == datetime.date(2025, 5, 10)
