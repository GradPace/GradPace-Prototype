import pytest

from accounts.factories import RoleFactory, StudentProfileFactory, UserFactory
from accounts.tests.helpers import login
from benchmarks.catalog import skill_catalog

from ..factories import AlumniSurveyResponseFactory, AlumniUserFactory
from ..models import AlumniSurveyResponse

URL = '/api/survey/alumni/'

REQUIRED_FIELDS = [
    'current_job_title',
    'industry',
    'top_skills',
    'preparedness_rating',
    'platform_helpfulness_rating',
    'suggested_skills',
    'platform_feedback',
]


@pytest.fixture
def catalog_skills(db):
    """Real catalog names. The intelligence migrations seed the jobs the
    catalog is built from."""
    return [skill['name'] for skill in skill_catalog()[:6]]


@pytest.fixture
def payload(catalog_skills):
    return {
        'current_job_title': 'Junior Software Engineer',
        'industry': 'software',
        'top_skills': catalog_skills[:3],
        'preparedness_rating': 4,
        'platform_helpfulness_rating': 5,
        'suggested_skills': ['Rust', 'LLM tooling'],
        'platform_feedback': 'The gap list told me exactly what to study.',
    }


def auth(client, user):
    return {'HTTP_AUTHORIZATION': f'Bearer {login(client, user)["access"]}'}


def post(client, user, data):
    return client.post(URL, data, content_type='application/json', **auth(client, user))


# --- Access (FR-01) --------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize('method', ['get', 'post'])
def test_requires_authentication(client, method):
    response = getattr(client, method)(URL)

    assert response.status_code == 401


@pytest.mark.django_db
def test_students_cannot_open_the_survey(client):
    student = StudentProfileFactory().user

    response = client.get(URL, **auth(client, student))

    assert response.status_code == 403


@pytest.mark.django_db
def test_students_cannot_submit_the_survey(client, payload):
    student = StudentProfileFactory().user

    response = post(client, student, payload)

    assert response.status_code == 403
    assert not AlumniSurveyResponse.objects.exists()


@pytest.mark.django_db
@pytest.mark.parametrize('role', ['admin', None])
def test_other_roles_cannot_submit(client, payload, role):
    user = UserFactory(role=RoleFactory(role_name=role) if role else None)

    response = post(client, user, payload)

    assert response.status_code == 403


# --- Submitting (FR-02, FR-04) ----------------------------------------------


@pytest.mark.django_db
def test_alum_can_submit(client, payload):
    alum = AlumniUserFactory()

    response = post(client, alum, payload)

    assert response.status_code == 201
    body = response.json()
    for field in REQUIRED_FIELDS:
        assert body[field] == payload[field]
    assert 'user' not in body

    saved = AlumniSurveyResponse.objects.get()
    assert saved.user == alum
    assert saved.submitted_at is not None
    assert str(saved.id) == body['id']


@pytest.mark.django_db
def test_user_and_submitted_at_come_from_the_server(client, payload):
    alum = AlumniUserFactory()
    other = AlumniUserFactory()

    response = post(
        client,
        alum,
        {**payload, 'user': str(other.pk), 'submitted_at': '2000-01-01T00:00:00Z'},
    )

    assert response.status_code == 201
    saved = AlumniSurveyResponse.objects.get()
    assert saved.user == alum
    assert saved.submitted_at.year != 2000


@pytest.mark.django_db
def test_second_submission_is_rejected(client, payload):
    alum = AlumniUserFactory()
    post(client, alum, payload)

    response = post(client, alum, {**payload, 'preparedness_rating': 1})

    assert response.status_code == 400
    assert response.json() == {'detail': 'Survey already submitted.'}
    assert AlumniSurveyResponse.objects.get().preparedness_rating == 4


@pytest.mark.django_db
def test_get_404s_before_submitting(client):
    alum = AlumniUserFactory()

    response = client.get(URL, **auth(client, alum))

    assert response.status_code == 404


@pytest.mark.django_db
def test_get_returns_own_response(client):
    survey = AlumniSurveyResponseFactory()
    AlumniSurveyResponseFactory(current_job_title='Someone else')

    response = client.get(URL, **auth(client, survey.user))

    assert response.status_code == 200
    assert response.json()['id'] == str(survey.id)
    assert response.json()['current_job_title'] == 'Software Engineer'


# --- Validation (FR-03) ------------------------------------------------------


@pytest.mark.django_db
@pytest.mark.parametrize('field', REQUIRED_FIELDS)
def test_every_field_is_required(client, payload, field):
    del payload[field]

    response = post(client, AlumniUserFactory(), payload)

    assert response.status_code == 400
    assert field in response.json()


@pytest.mark.django_db
@pytest.mark.parametrize('field', ['current_job_title', 'industry', 'platform_feedback'])
def test_text_answers_cannot_be_blank(client, payload, field):
    payload[field] = '   '

    response = post(client, AlumniUserFactory(), payload)

    assert response.status_code == 400
    assert field in response.json()


@pytest.mark.django_db
def test_unknown_industry_is_rejected(client, payload):
    payload['industry'] = 'space-piracy'

    response = post(client, AlumniUserFactory(), payload)

    assert response.status_code == 400
    assert 'industry' in response.json()


@pytest.mark.django_db
@pytest.mark.parametrize('field', ['preparedness_rating', 'platform_helpfulness_rating'])
@pytest.mark.parametrize('value', [0, 6, 'great'])
def test_ratings_must_be_1_to_5(client, payload, field, value):
    payload[field] = value

    response = post(client, AlumniUserFactory(), payload)

    assert response.status_code == 400
    assert field in response.json()


@pytest.mark.django_db
def test_top_skills_must_be_from_the_catalog(client, payload):
    payload['top_skills'] = [payload['top_skills'][0], 'Not A Real Skill']

    response = post(client, AlumniUserFactory(), payload)

    assert response.status_code == 400
    assert 'Not A Real Skill' in str(response.json()['top_skills'])


@pytest.mark.django_db
def test_top_skills_cannot_repeat(client, payload):
    payload['top_skills'] = [payload['top_skills'][0]] * 2

    response = post(client, AlumniUserFactory(), payload)

    assert response.status_code == 400
    assert 'top_skills' in response.json()


@pytest.mark.django_db
@pytest.mark.parametrize('count', [0, 6])
def test_top_skills_count_is_1_to_5(client, payload, catalog_skills, count):
    payload['top_skills'] = catalog_skills[:count]

    response = post(client, AlumniUserFactory(), payload)

    assert response.status_code == 400
    assert 'top_skills' in response.json()


@pytest.mark.django_db
@pytest.mark.parametrize(
    'suggested',
    [
        [],
        ['a', 'b', 'c', 'd', 'e', 'f'],
        ['Rust', '  '],
        ['Rust', 'rust'],
        ['x' * 101],
    ],
    ids=['empty', 'too-many', 'blank-item', 'case-duplicate', 'too-long'],
)
def test_suggested_skills_validation(client, payload, suggested):
    payload['suggested_skills'] = suggested

    response = post(client, AlumniUserFactory(), payload)

    assert response.status_code == 400
    assert 'suggested_skills' in response.json()


@pytest.mark.django_db
def test_suggested_skills_are_trimmed(client, payload):
    payload['suggested_skills'] = ['  Rust  ']

    response = post(client, AlumniUserFactory(), payload)

    assert response.status_code == 201
    assert AlumniSurveyResponse.objects.get().suggested_skills == ['Rust']
