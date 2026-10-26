"""The GP-82 demo benchmark - scoring_demo.py's math, plus the demo
benchmark, endpoints and seed command against the real seed data."""

from io import StringIO

import pytest
from django.core.management import CommandError, call_command
from rest_framework.test import APIClient

from accounts.factories import StudentProfileFactory, UserFactory
from accounts.models import StudentProfile
from benchmarks.management.commands.seed_demo_students_demo import DEMO_STUDENTS
from intelligence.models import JobSkill

from ..job_benchmark_demo import (
    ROLE_SOC_CODE,
    SKILL_GROUPS,
    SkillGroup,
    build_job_benchmark_demo,
    get_demo_job,
)
from ..scoring_demo import (
    CERT_BONUS_EACH,
    CERT_BONUS_MAX,
    CERTIFICATES,
    COURSES,
    COURSES_POINTS,
    MAX_SCORE,
    NEXT_STEPS_COUNT,
    SKILLS_POINTS,
    certificate_bonus,
    level_of,
    readiness_demo,
    score_courses,
    score_skills,
    score_student_demo,
)


def group(key, tools, weight=1.0):
    return SkillGroup(key=key, name=key.title(), tools=tuple(tools), weight=weight)


def skills_points(student, groups):
    points, _ = score_skills(student, groups)
    return points


ALL_COURSES = [code for code, _ in COURSES]


# --- Levels: Skill.proficiency_level -> share of a group's points ---


@pytest.mark.parametrize(
    ('text', 'label', 'credit'),
    [
        ('beginner', 'Learning', 0.25),
        ('intermediate', 'Practicing', 0.60),
        ('expert', 'Project ready', 1.00),
        ('advanced', 'Practicing', 0.60),  # older rows
        ('', 'Learning', 0.25),  # unrated
    ],
)
def test_level_of(text, label, credit):
    assert level_of(text) == (label, credit)


# --- Skills: best tool per group, groups weighted by demand ---


@pytest.mark.parametrize(
    ('text', 'expected'),
    [('beginner', 12.5), ('intermediate', 30.0), ('expert', 50.0)],
)
def test_level_scales_group_points(text, expected):
    assert skills_points({'React': text}, [group('frontend', ['React'])]) == expected


def test_best_tool_in_group_counts():
    frontend = group('frontend', ['React', 'Google Angular'])
    student = {'React': 'beginner', 'Google Angular': 'expert'}

    points, [detail] = score_skills(student, [frontend])

    assert points == SKILLS_POINTS
    assert detail['best_tool'] == 'Angular'
    assert detail['level'] == 'Project ready'


def test_second_tool_in_group_adds_nothing():
    frontend = group('frontend', ['React', 'Google Angular'])
    one = skills_points({'React': 'expert'}, [frontend])
    both = skills_points({'React': 'expert', 'Google Angular': 'expert'}, [frontend])
    assert one == both == SKILLS_POINTS


def test_groups_split_points_by_weight():
    groups = [group('language', ['Python'], 0.75), group('cloud', ['AWS'], 0.25)]

    _, details = score_skills({}, groups)

    assert [d['out_of'] for d in details] == [37.5, 12.5]
    assert all(d['points'] == 0 for d in details)


@pytest.mark.parametrize('typed', ['Structured query language SQL', 'SQL', '  sql '])
def test_tool_matches_by_name_or_label(typed):
    databases = group('databases', ['Structured query language SQL'])
    assert skills_points({typed: 'expert'}, [databases]) == SKILLS_POINTS


def test_skill_outside_every_group_earns_nothing():
    assert skills_points({'Microsoft Excel': 'expert'}, [group('os', ['Linux'])]) == 0


# --- Courses ---


def test_each_course_is_an_equal_share():
    points, details = score_courses(ALL_COURSES[:2])

    assert points == pytest.approx(2 * COURSES_POINTS / len(COURSES))
    assert [d['taken'] for d in details[:3]] == [True, True, False]


def test_course_code_ignores_case_and_spaces():
    code = ALL_COURSES[0]
    points, _ = score_courses([code.lower().replace(' ', '')])
    assert points == pytest.approx(COURSES_POINTS / len(COURSES))


def test_all_courses_earn_full_points():
    points, _ = score_courses(ALL_COURSES)
    assert points == pytest.approx(COURSES_POINTS)


def test_course_not_on_the_list_earns_nothing():
    assert score_courses(['MATH 211'])[0] == 0


# --- Certificate bonus ---


def test_certificate_bonus_per_certificate():
    assert certificate_bonus([CERTIFICATES[0]]) == (CERT_BONUS_EACH, [CERTIFICATES[0]])


def test_certificate_bonus_is_capped():
    bonus, counted = certificate_bonus(CERTIFICATES)
    assert bonus == CERT_BONUS_MAX
    assert counted == CERTIFICATES


def test_certificate_matches_ignoring_case():
    assert certificate_bonus([CERTIFICATES[0].upper()])[0] == CERT_BONUS_EACH


def test_unknown_certificate_earns_nothing():
    assert certificate_bonus(['Food Handler Certificate']) == (0, [])


# --- Overall ---


def test_overall_is_skills_plus_courses_plus_bonus():
    groups = [group('language', ['Python'])]

    result = readiness_demo({'Python': 'intermediate'}, ALL_COURSES[:6], CERTIFICATES[:1], groups)

    courses = 6 * COURSES_POINTS / len(COURSES)
    expected = 30.0 + courses + CERT_BONUS_EACH
    assert result['overall_readiness_score'] == pytest.approx(expected, abs=0.01)
    assert set(result['gap_breakdown']) == {'skills', 'courses'}


def test_overall_is_capped():
    groups = [group('language', ['Python'])]

    result = readiness_demo({'Python': 'expert'}, ALL_COURSES, CERTIFICATES, groups)

    assert result['overall_readiness_score'] == MAX_SCORE


def test_next_steps_are_the_biggest_gains_first():
    groups = [
        group('language', ['Python'], 0.6),  # 30 points
        group('cloud', ['AWS'], 0.3),  # 15 points
        group('os', ['Linux'], 0.1),  # 5 points
    ]

    steps = readiness_demo({}, [], [], groups)['next_steps']

    assert len(steps) == NEXT_STEPS_COUNT
    assert [s['name'] for s in steps[:2]] == ['Language', 'Cloud']
    points = [s['points_available'] for s in steps]
    assert points == sorted(points, reverse=True)


# --- The demo benchmark on the real seed data ---


def test_every_group_tool_is_a_real_job_skill(real_catalog):
    """Guards against a typo in SKILL_GROUPS silently scoring nothing."""
    job_skills = set(JobSkill.objects.filter(job=get_demo_job()).values_list('name', flat=True))
    for _, name, tools in SKILL_GROUPS:
        assert set(tools) <= job_skills, name


def test_demo_benchmark_uses_norfolk_postings(real_catalog):
    benchmark = build_job_benchmark_demo(get_demo_job())

    assert benchmark.job.soc_code == ROLE_SOC_CODE
    assert benchmark.postings_used > 0
    assert len(benchmark.groups) == len(SKILL_GROUPS)
    assert all(0 < g.weight <= 1 for g in benchmark.groups)


# --- Endpoints ---


def api(user):
    client = APIClient()
    client.force_authenticate(user)
    return client


def test_options_lists_everything_the_pickers_need(real_catalog):
    response = api(UserFactory()).get('/api/benchmark/demo/options/')

    assert response.status_code == 200
    data = response.json()
    assert len(data['skill_groups']) == len(SKILL_GROUPS)
    assert sum(g['points'] for g in data['skill_groups']) == pytest.approx(SKILLS_POINTS, abs=0.1)
    assert [c['code'] for c in data['courses']] == ALL_COURSES
    assert data['certificates'] == CERTIFICATES
    assert [lvl['value'] for lvl in data['levels']] == ['beginner', 'intermediate', 'expert']


def test_demo_endpoints_need_login(db):
    client = APIClient()
    assert client.get('/api/benchmark/demo/options/').status_code == 401
    assert client.get('/api/benchmark/demo/me/').status_code == 401


def test_me_needs_a_student_profile(real_catalog):
    assert api(UserFactory()).get('/api/benchmark/demo/me/').status_code == 404


def test_me_needs_job_data(db):
    # The autouse fixture leaves no jobs, as if migrations hadn't seeded them.
    student = StudentProfileFactory()
    assert api(student.user).get('/api/benchmark/demo/me/').status_code == 404


def test_me_scores_without_saving(real_catalog):
    student = StudentProfileFactory(readiness_score=12.0)

    response = api(student.user).get('/api/benchmark/demo/me/')

    assert response.status_code == 200
    assert response.json()['role']['soc_code'] == ROLE_SOC_CODE
    student.refresh_from_db()
    assert student.readiness_score == 12.0


# --- seed_demo_students_demo ---


def run_seed(**options):
    call_command('seed_demo_students_demo', password='Zq7!fWbn2', stdout=StringIO(), **options)


def demo_profile(data):
    return StudentProfile.objects.get(user__email=data['email'])


def test_seed_refuses_with_debug_off(settings, real_catalog):
    settings.DEBUG = False
    with pytest.raises(CommandError, match='production'):
        run_seed()


def test_seed_creates_students_with_skills_courses_and_certificates(settings, real_catalog):
    settings.DEBUG = True
    run_seed()

    for data in DEMO_STUDENTS:
        student = demo_profile(data)
        assert student.skills.count() == len(data['skills'])
        assert student.taken_classes.count() == len(data['courses'])
        assert student.certificates.count() == len(data['certificates'])


def test_seed_students_show_the_intended_story(settings, real_catalog):
    settings.DEBUG = True
    run_seed()
    benchmark = build_job_benchmark_demo(get_demo_job())

    scores = [
        score_student_demo(demo_profile(data), benchmark)['overall_readiness_score']
        for data in DEMO_STUDENTS
    ]
    # Alex > Priya > Marcus, and even Alex isn't a perfect 100.
    assert scores == sorted(scores, reverse=True)
    assert scores[0] < MAX_SCORE


def test_seed_rerun_resets_instead_of_duplicating(settings, real_catalog):
    settings.DEBUG = True
    run_seed()
    run_seed()

    first = demo_profile(DEMO_STUDENTS[0])
    assert first.taken_classes.count() == len(DEMO_STUDENTS[0]['courses'])
    assert StudentProfile.objects.count() == len(DEMO_STUDENTS)
