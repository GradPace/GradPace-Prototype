"""The benchmark app's API endpoints."""

import pytest

from accounts.factories import SkillFactory, StudentProfileFactory, UserFactory
from accounts.tests.helpers import login
from intelligence.factories import JobFactory, JobPostingFactory, JobSkillFactory


def auth_header(client, user):
    tokens = login(client, user)
    return {'HTTP_AUTHORIZATION': f'Bearer {tokens["access"]}'}


@pytest.fixture
def job(db):
    """Software Developers: Git in both postings, SQL in one."""
    job = JobFactory(title='Software Developers', soc_code='15-1252')
    git = JobSkillFactory(job=job, name='Git', skill_type='software')
    sql = JobSkillFactory(job=job, name='Structured query language SQL', skill_type='software')
    JobPostingFactory(job=job, seniority='entry', skills=[git, sql])
    JobPostingFactory(job=job, seniority='entry', skills=[git])
    return job


@pytest.fixture
def student(db):
    return StudentProfileFactory()


# --- /roles/ and /roles/<soc>/ ---


def test_roles_lists_jobs(client, job, student):
    response = client.get('/api/benchmark/roles/', **auth_header(client, student.user))

    assert response.status_code == 200
    assert response.json() == [
        {'soc_code': '15-1252', 'title': 'Software Developers', 'posting_count': 2}
    ]


def test_job_benchmark_shows_weighted_skills(client, job, student):
    response = client.get('/api/benchmark/roles/15-1252/', **auth_header(client, student.user))

    assert response.status_code == 200
    body = response.json()
    assert body['role'] == {'soc_code': '15-1252', 'title': 'Software Developers'}
    assert body['postings_used'] == 2
    assert body['skills'][0] == {
        'name': 'Git',
        'label': 'Git',
        'skill_type': 'software',
        'weight': 1.0,
    }
    assert body['skills'][1]['label'] == 'SQL'


def test_job_benchmark_404s_on_unknown_job(client, student):
    response = client.get('/api/benchmark/roles/99-9999/', **auth_header(client, student.user))
    assert response.status_code == 404


# --- /skills/ ---


def test_skill_catalog_lists_benchmark_skills_with_labels(client, job, student):
    other = JobFactory(title='Web Developers', soc_code='15-1254')
    git = JobSkillFactory(job=other, name='Git', skill_type='software')
    JobPostingFactory(job=other, seniority='entry', skills=[git])

    response = client.get('/api/benchmark/skills/', **auth_header(client, student.user))

    assert response.status_code == 200
    assert response.json() == [
        # Git is in both jobs' benchmarks, so it comes first
        {'name': 'Git', 'label': 'Git', 'skill_type': 'software', 'job_count': 2, 'demand': 1.0},
        {
            'name': 'Structured query language SQL',
            'label': 'SQL',
            'skill_type': 'software',
            'job_count': 1,
            'demand': 0.5,
        },
    ]


def test_skill_catalog_can_be_limited_to_one_role(client, job, student):
    other = JobFactory(title='Web Developers', soc_code='15-1254')
    css = JobSkillFactory(job=other, name='Cascading style sheets CSS', skill_type='software')
    JobPostingFactory(job=other, seniority='entry', skills=[css])

    response = client.get(
        '/api/benchmark/skills/?role=15-1252', **auth_header(client, student.user)
    )

    assert response.status_code == 200
    names = [s['name'] for s in response.json()]
    # Most in-demand first (Git 1.0, SQL 0.5), and no CSS - not in this job's benchmark
    assert names == ['Git', 'Structured query language SQL']


def test_skill_catalog_400s_on_unknown_role(client, job, student):
    response = client.get(
        '/api/benchmark/skills/?role=99-9999', **auth_header(client, student.user)
    )
    assert response.status_code == 400
    assert 'role' in response.json()


def test_endpoints_require_authentication(client, job):
    for url in [
        '/api/benchmark/roles/',
        '/api/benchmark/roles/15-1252/',
        '/api/benchmark/skills/',
        '/api/benchmark/me/?role=15-1252',
        '/api/benchmark/me/best-fit/',
    ]:
        assert client.get(url).status_code == 401, url


# --- /me/ ---


def test_me_404s_without_student_profile(client, job):
    response = client.get('/api/benchmark/me/?role=15-1252', **auth_header(client, UserFactory()))
    assert response.status_code == 404


def test_me_400s_on_unknown_role(client, student):
    response = client.get('/api/benchmark/me/?role=99-9999', **auth_header(client, student.user))
    assert response.status_code == 400
    assert 'role' in response.json()


def test_me_400s_with_no_role_and_no_target_job(client, student):
    response = client.get('/api/benchmark/me/', **auth_header(client, student.user))
    assert response.status_code == 400
    assert 'role' in response.json()


def test_me_scores_own_skills_and_saves_score_for_target_job(client, job, student):
    student.target_job = job
    student.save()
    SkillFactory(student=student, name='Git', proficiency_level='expert')
    SkillFactory(
        student=student, name='Structured query language SQL', proficiency_level='intermediate'
    )

    response = client.get('/api/benchmark/me/', **auth_header(client, student.user))

    assert response.status_code == 200
    body = response.json()
    assert body['role'] == {'soc_code': '15-1252', 'title': 'Software Developers'}
    assert body['benchmark'] == {'postings_used': 2, 'seniorities_used': 'all'}
    # Git: weight 1.0, expert = full credit. SQL: weight 0.5, intermediate = 50%
    # -> (1.0 + 0.25) / 1.5
    assert body['overall_readiness_score'] == pytest.approx(83.33)
    assert body['skills']['software'][1]['your_level'] == 2
    assert body['saved_to_profile'] is True

    student.refresh_from_db()
    assert student.readiness_score == body['overall_readiness_score']


def test_me_for_another_role_doesnt_overwrite_saved_score(client, job, student):
    other = JobFactory(title='Web Developers', soc_code='15-1254')
    student.target_job = other
    student.readiness_score = 42.0
    student.save()
    SkillFactory(student=student, name='Git', proficiency_level='expert')

    response = client.get('/api/benchmark/me/?role=15-1252', **auth_header(client, student.user))

    assert response.json()['saved_to_profile'] is False
    student.refresh_from_db()
    assert student.readiness_score == 42.0


def test_me_uses_saved_target_job_when_no_role_given(client, job, student):
    student.target_job = job
    student.save()
    SkillFactory(student=student, name='Git', proficiency_level='expert')

    response = client.get('/api/benchmark/me/', **auth_header(client, student.user))

    assert response.status_code == 200
    assert response.json()['role']['soc_code'] == '15-1252'


def test_me_role_param_overrides_saved_target_job(client, job, student):
    other = JobFactory(title='Web Developers', soc_code='15-1254')
    student.target_job = other
    student.save()

    response = client.get('/api/benchmark/me/?role=15-1252', **auth_header(client, student.user))

    assert response.json()['role']['soc_code'] == '15-1252'


def test_me_only_uses_callers_own_skills(client, job, student):
    someone_else = StudentProfileFactory()
    SkillFactory(student=someone_else, name='Git', proficiency_level='expert')

    response = client.get('/api/benchmark/me/?role=15-1252', **auth_header(client, student.user))

    assert response.json()['overall_readiness_score'] == 0.0


# --- /me/best-fit/ ---


def test_best_fit_ranks_jobs_by_readiness(client, job, student):
    # job (Software Developers) wants Git + SQL; Web Developers wants CSS
    other = JobFactory(title='Web Developers', soc_code='15-1254')
    css = JobSkillFactory(job=other, name='Cascading style sheets CSS', skill_type='software')
    JobPostingFactory(job=other, seniority='entry', skills=[css])
    SkillFactory(student=student, name='CSS', proficiency_level='expert')

    response = client.get('/api/benchmark/me/best-fit/', **auth_header(client, student.user))

    assert response.status_code == 200
    body = response.json()
    assert [r['role']['title'] for r in body] == ['Web Developers', 'Software Developers']
    assert body[0]['overall_readiness_score'] == 100.0
    assert body[0]['limited_data'] is True  # 1 posting
    assert body[1]['top_unmet_skills'][0]['label'] == 'Git'


def test_best_fit_404s_without_student_profile(client, job):
    response = client.get('/api/benchmark/me/best-fit/', **auth_header(client, UserFactory()))
    assert response.status_code == 404


def test_best_fit_doesnt_change_saved_score(client, job, student):
    student.readiness_score = 42.0
    student.save()

    client.get('/api/benchmark/me/best-fit/', **auth_header(client, student.user))

    student.refresh_from_db()
    assert student.readiness_score == 42.0


# --- /me/ and /me/options/ with a scoring config ---

from accounts.factories import CertificateFactory, TakenClassFactory  # noqa: E402

from ..config import ODU_SOFTWARE_DEVELOPER as CONFIG  # noqa: E402


@pytest.fixture
def odu_student(db, job):
    return StudentProfileFactory(uni=CONFIG.school, location=CONFIG.location, target_job=job)


def test_me_without_a_config_has_no_config_fields(client, job, student):
    student.target_job = job
    student.save()

    body = client.get('/api/benchmark/me/', **auth_header(client, student.user)).json()

    assert not {'skill_groups', 'courses', 'certificates', 'next_steps'} & body.keys()
    assert body['benchmark'] == {'postings_used': 2, 'seniorities_used': 'all'}


def test_me_with_a_config_adds_groups_courses_and_certificates(client, job, odu_student):
    SkillFactory(student=odu_student, name='Git', proficiency_level='expert')
    TakenClassFactory(student=odu_student, course_code='cs 361')
    CertificateFactory(student=odu_student, name=CONFIG.certificates[0])

    response = client.get('/api/benchmark/me/', **auth_header(client, odu_student.user))

    assert response.status_code == 200
    body = response.json()
    assert body['benchmark']['school'] == CONFIG.school
    assert body['benchmark']['location'] == CONFIG.location
    assert set(body['gap_breakdown']) == {'skills', 'courses'}
    # The base shape is still there.
    assert 'software' in body['skills']
    assert 'flagged_gaps' in body

    groups = {g['key']: g for g in body['skill_groups']['groups']}
    assert groups['version_control']['best_tool'] == 'Git'
    assert groups['version_control']['level'] == 'Project ready'
    assert [c['taken'] for c in body['courses']['list']].count(True) == 1
    assert body['certificates']['counted'] == [CONFIG.certificates[0]]
    assert body['certificates']['bonus'] == CONFIG.cert_bonus_each
    assert len(body['next_steps']) == CONFIG.next_steps_count
    # Weights: version control 1.0 (Git in both postings), databases 0.5 (SQL in
    # one), the rest 0 - so expert Git earns 1.0 / 1.5 of the 50 skill points.
    skills_points = CONFIG.skills_points / 1.5
    assert body['skill_groups']['points'] == pytest.approx(skills_points, abs=0.01)
    courses_points = CONFIG.courses_points / len(CONFIG.courses)
    assert body['overall_readiness_score'] == pytest.approx(
        skills_points + courses_points + CONFIG.cert_bonus_each, abs=0.02
    )


def test_me_with_a_config_only_uses_postings_in_its_location(client, job, odu_student):
    JobPostingFactory(job=job, location='Austin, TX', seniority='entry')

    body = client.get('/api/benchmark/me/', **auth_header(client, odu_student.user)).json()

    assert body['benchmark']['postings_used'] == 2  # not 3


def test_me_with_a_config_saves_the_configured_score(client, job, odu_student):
    SkillFactory(student=odu_student, name='Git', proficiency_level='expert')

    body = client.get('/api/benchmark/me/', **auth_header(client, odu_student.user)).json()

    odu_student.refresh_from_db()
    assert body['saved_to_profile'] is True
    assert odu_student.readiness_score == body['overall_readiness_score']


OPTIONS_URL = (
    f'/api/benchmark/options/?role=15-1252&school={CONFIG.school}&location={CONFIG.location}'
)


def test_options_lists_everything_the_pickers_need(client, job, student):
    response = client.get(OPTIONS_URL, **auth_header(client, student.user))

    assert response.status_code == 200
    data = response.json()
    assert data['role'] == {'soc_code': '15-1252', 'title': 'Software Developers'}
    assert [g['key'] for g in data['skill_groups']] == [k for k, _, _ in CONFIG.skill_groups]
    assert sum(g['points'] for g in data['skill_groups']) == pytest.approx(
        CONFIG.skills_points, abs=0.1
    )
    assert [c['code'] for c in data['courses']] == [c for c, _ in CONFIG.courses]
    assert data['certificates'] == list(CONFIG.certificates)
    assert [lvl['value'] for lvl in data['levels']] == ['beginner', 'intermediate', 'expert']


def test_options_works_before_the_student_has_a_profile(client, job):
    response = client.get(OPTIONS_URL, **auth_header(client, UserFactory()))
    assert response.status_code == 200


@pytest.mark.parametrize(
    'query',
    [
        '',
        '?role=15-1252',
        '?role=99-9999&school=Old Dominion University&location=Norfolk, VA',
        '?role=15-1252&school=Other U&location=Norfolk, VA',
        '?role=15-1252&school=Old Dominion University&location=Austin, TX',
    ],
)
def test_options_404s_when_no_config_matches(client, job, student, query):
    response = client.get(f'/api/benchmark/options/{query}', **auth_header(client, student.user))
    assert response.status_code == 404


def test_options_requires_authentication(client, job):
    assert client.get(OPTIONS_URL).status_code == 401
