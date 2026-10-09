import pytest

from ..factories import SkillFactory, StudentProfileFactory, UserFactory
from ..models import Skill
from .helpers import login


def make_skill_payload(**overrides):
    payload = {'name': 'Python', 'proficiency_level': 'advanced'}
    payload.update(overrides)
    return payload


@pytest.mark.django_db
def test_list_requires_authentication(client):
    response = client.get('/api/auth/profile/skills/')

    assert response.status_code == 401


@pytest.mark.django_db
def test_create_requires_authentication(client):
    response = client.post(
        '/api/auth/profile/skills/',
        make_skill_payload(),
        content_type='application/json',
    )

    assert response.status_code == 401


@pytest.mark.django_db
def test_create_requires_a_profile(client):
    user = UserFactory()
    tokens = login(client, user)

    response = client.post(
        '/api/auth/profile/skills/',
        make_skill_payload(),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}',
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_create_succeeds_and_is_scoped_to_the_caller(client):
    profile = StudentProfileFactory()
    tokens = login(client, profile.user)

    response = client.post(
        '/api/auth/profile/skills/',
        make_skill_payload(),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}',
    )

    assert response.status_code == 201
    body = response.json()
    assert body['name'] == 'Python'
    assert body['proficiency_level'] == 'advanced'

    skill = Skill.objects.get(id=body['id'])
    assert skill.student == profile


@pytest.mark.django_db
def test_create_rejects_a_duplicate_skill_name(client):
    profile = StudentProfileFactory()
    SkillFactory(student=profile, name='Python')
    tokens = login(client, profile.user)

    response = client.post(
        '/api/auth/profile/skills/',
        make_skill_payload(name='Python'),
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}',
    )

    assert response.status_code == 400


@pytest.mark.django_db
def test_list_only_returns_the_callers_own_skills(client):
    profile = StudentProfileFactory()
    other_profile = StudentProfileFactory()
    SkillFactory(student=profile, name='Python')
    SkillFactory(student=other_profile, name='Go')
    tokens = login(client, profile.user)

    response = client.get(
        '/api/auth/profile/skills/',
        HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}',
    )

    assert response.status_code == 200
    names = [entry['name'] for entry in response.json()['results']]
    assert names == ['Python']


@pytest.mark.django_db
def test_retrieve_another_users_skill_is_404(client):
    profile = StudentProfileFactory()
    other_skill = SkillFactory()
    tokens = login(client, profile.user)

    response = client.get(
        f'/api/auth/profile/skills/{other_skill.id}/',
        HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}',
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_update_only_changes_given_fields(client):
    profile = StudentProfileFactory()
    skill = SkillFactory(student=profile, name='Python', proficiency_level='beginner')
    tokens = login(client, profile.user)

    response = client.patch(
        f'/api/auth/profile/skills/{skill.id}/',
        {'proficiency_level': 'expert'},
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}',
    )

    assert response.status_code == 200
    body = response.json()
    assert body['proficiency_level'] == 'expert'
    assert body['name'] == 'Python'


@pytest.mark.django_db
def test_update_another_users_skill_is_404(client):
    profile = StudentProfileFactory()
    other_skill = SkillFactory()
    tokens = login(client, profile.user)

    response = client.patch(
        f'/api/auth/profile/skills/{other_skill.id}/',
        {'proficiency_level': 'expert'},
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}',
    )

    assert response.status_code == 404


@pytest.mark.django_db
def test_delete_removes_the_skill(client):
    profile = StudentProfileFactory()
    skill = SkillFactory(student=profile)
    tokens = login(client, profile.user)

    response = client.delete(
        f'/api/auth/profile/skills/{skill.id}/',
        HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}',
    )

    assert response.status_code == 204
    assert not Skill.objects.filter(id=skill.id).exists()


@pytest.mark.django_db
def test_delete_another_users_skill_is_404(client):
    profile = StudentProfileFactory()
    other_skill = SkillFactory()
    tokens = login(client, profile.user)

    response = client.delete(
        f'/api/auth/profile/skills/{other_skill.id}/',
        HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}',
    )

    assert response.status_code == 404
    assert Skill.objects.filter(id=other_skill.id).exists()
