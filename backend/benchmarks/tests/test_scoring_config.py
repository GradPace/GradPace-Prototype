"""Scoring under a ScoringConfig (config.py, scoring.readiness_configured):
skill groups + courses + certificate bonus. Ported from the GP-82 demo."""

import pytest

from accounts.factories import StudentProfileFactory
from intelligence.factories import JobFactory
from intelligence.models import JobSkill

from ..config import ODU_SOFTWARE_DEVELOPER as CONFIG
from ..config import ScoringConfig, get_config
from ..job_benchmark import SkillGroup, build_job_benchmark, get_job
from ..scoring import (
    certificate_bonus,
    next_steps,
    readiness_configured,
    score_courses,
)

ALL_COURSES = [code for code, _ in CONFIG.courses]
CERTIFICATES = list(CONFIG.certificates)


def group(key, tools, weight=1.0):
    return SkillGroup(key=key, name=key.title(), tools=tuple(tools), weight=weight)


def run(skills=None, courses=(), certificates=(), groups=None):
    groups = groups or [group('language', ['Python'])]
    return readiness_configured(skills or {}, courses, certificates, groups, CONFIG)


# --- levels ---


@pytest.mark.parametrize(
    ('text', 'label', 'credit'),
    [
        ('beginner', 'Learning', 0.25),
        ('intermediate', 'Practicing', 0.60),
        ('expert', 'Project ready', 1.00),
        ('advanced', 'Practicing', 0.60),  # older rows
        ('', 'Learning', 0.25),  # unrated
        ('wizard', 'Learning', 0.25),  # unknown
    ],
)
def test_level_credit(text, label, credit):
    assert CONFIG.level_credit(text) == (label, credit)


@pytest.mark.parametrize(
    ('text', 'expected'),
    [('beginner', 12.5), ('intermediate', 30.0), ('expert', 50.0)],
)
def test_level_scales_group_points(text, expected):
    result = run({'Python': text})
    assert result['skill_groups']['points'] == expected


# --- courses ---


def test_each_course_is_an_equal_share():
    points, details = score_courses(ALL_COURSES[:2], CONFIG)

    assert points == pytest.approx(2 * CONFIG.courses_points / len(CONFIG.courses))
    assert [d['taken'] for d in details[:3]] == [True, True, False]


def test_course_code_ignores_case_and_spaces():
    points, _ = score_courses([ALL_COURSES[0].lower().replace(' ', '')], CONFIG)
    assert points == pytest.approx(CONFIG.courses_points / len(CONFIG.courses))


def test_all_courses_earn_full_points():
    assert score_courses(ALL_COURSES, CONFIG)[0] == pytest.approx(CONFIG.courses_points)


def test_course_not_on_the_list_earns_nothing():
    assert score_courses(['MATH 211'], CONFIG)[0] == 0


# --- certificate bonus ---


def test_certificate_bonus_per_certificate():
    assert certificate_bonus([CERTIFICATES[0]], CONFIG) == (
        CONFIG.cert_bonus_each,
        [CERTIFICATES[0]],
    )


def test_certificate_bonus_is_capped():
    bonus, counted = certificate_bonus(CERTIFICATES, CONFIG)
    assert bonus == CONFIG.cert_bonus_max
    assert counted == CERTIFICATES


def test_certificate_matches_ignoring_case():
    assert certificate_bonus([CERTIFICATES[0].upper()], CONFIG)[0] == CONFIG.cert_bonus_each


def test_unknown_certificate_earns_nothing():
    assert certificate_bonus(['Food Handler Certificate'], CONFIG) == (0, [])


# --- overall ---


def test_overall_is_skills_plus_courses_plus_bonus():
    result = run({'Python': 'intermediate'}, ALL_COURSES[:6], CERTIFICATES[:1])

    courses = 6 * CONFIG.courses_points / len(CONFIG.courses)
    expected = 30.0 + courses + CONFIG.cert_bonus_each
    assert result['overall_readiness_score'] == pytest.approx(expected, abs=0.01)
    assert set(result['gap_breakdown']) == {'skills', 'courses'}


def test_overall_is_capped():
    result = run({'Python': 'expert'}, ALL_COURSES, CERTIFICATES)
    assert result['overall_readiness_score'] == CONFIG.max_score


def test_next_steps_are_the_biggest_gains_first():
    groups = [
        group('language', ['Python'], 0.6),  # 30 points
        group('cloud', ['AWS'], 0.3),  # 15 points
        group('os', ['Linux'], 0.1),  # 5 points
    ]

    steps = run(groups=groups)['next_steps']

    assert len(steps) == CONFIG.next_steps_count
    assert [s['name'] for s in steps[:2]] == ['Language', 'Cloud']
    points = [s['points_available'] for s in steps]
    assert points == sorted(points, reverse=True)


def test_next_steps_skip_what_is_already_earned():
    groups = [group('language', ['Python'])]
    done = readiness_configured({'Python': 'expert'}, ALL_COURSES, [], groups, CONFIG)
    assert done['next_steps'] == []
    assert next_steps([], [], 3) == []


# --- which students get a config ---


@pytest.mark.django_db
def test_get_config_needs_role_school_and_location_to_match():
    job = JobFactory(soc_code=CONFIG.soc_code)
    odu = StudentProfileFactory(uni=CONFIG.school, location=CONFIG.location)

    assert get_config(odu, job) is CONFIG
    assert get_config(odu, JobFactory(soc_code='15-9999')) is None
    assert get_config(StudentProfileFactory(uni='Other U', location=CONFIG.location), job) is None
    assert get_config(StudentProfileFactory(uni=CONFIG.school, location='Austin, TX'), job) is None


@pytest.mark.django_db
def test_get_config_ignores_case_and_surrounding_spaces():
    job = JobFactory(soc_code=CONFIG.soc_code)
    student = StudentProfileFactory(uni=' old dominion university ', location='norfolk, va')
    assert get_config(student, job) is CONFIG


def test_config_levels_can_differ_per_config():
    other = ScoringConfig(
        soc_code='x',
        school='x',
        location='x',
        skill_groups=(),
        courses=(('A 1', 'A'),),
        certificates=(),
        levels={'beginner': ('Low', 0.5), 'expert': ('High', 1.0)},
    )
    assert other.level_credit('beginner') == ('Low', 0.5)


# --- the config against the real seed data ---


def test_every_group_tool_is_a_real_job_skill(real_catalog):
    """Guards against a typo in a config's skill groups silently scoring nothing."""
    job = get_job(CONFIG.soc_code)
    job_skills = set(JobSkill.objects.filter(job=job).values_list('name', flat=True))
    for _, name, tools in CONFIG.skill_groups:
        assert set(tools) <= job_skills, name


def test_config_benchmark_uses_postings_in_its_location(real_catalog):
    benchmark = build_job_benchmark(
        get_job(CONFIG.soc_code), location=CONFIG.location, skill_groups=CONFIG.skill_groups
    )

    assert benchmark.postings_used > 0
    assert len(benchmark.groups) == len(CONFIG.skill_groups)
    assert all(0 < g.weight <= 1 for g in benchmark.groups)
