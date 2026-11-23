"""Readiness scoring - the pure math in scoring.py (no database)."""

import pytest

from ..job_benchmark import BenchmarkSkill, SkillGroup
from ..scoring import (
    proficiency_level,
    readiness,
    score_against_benchmark,
    score_groups,
    singleton_groups,
)


def skill(name, weight, skill_type='software'):
    return BenchmarkSkill(name=name, skill_type=skill_type, weight=weight)


def software_score(student, benchmark):
    profile, _, _ = score_against_benchmark(student, benchmark)
    return profile['software']


# --- Proficiency: Skill.proficiency_level text -> 1-4 -> credit ---


@pytest.mark.parametrize(
    ('text', 'level'),
    [('beginner', 1), ('intermediate', 2), ('advanced', 3), ('expert', 4), ('', 1)],
)
def test_proficiency_level(text, level):
    assert proficiency_level(text) == level


@pytest.mark.parametrize(
    ('text', 'expected'),
    [('expert', 100.0), ('advanced', 75.0), ('intermediate', 50.0), ('beginner', 25.0), ('', 25.0)],
)
def test_proficiency_scales_credit(text, expected):
    assert software_score({'Git': text}, [skill('Git', 1.0)]) == expected


# --- Matching a student's skills to benchmark skills ---


@pytest.mark.parametrize(
    'typed',
    [
        'Structured query language SQL',  # exact O*NET name, as the picker saves it
        'SQL',  # the display label
        '  sql ',  # case and surrounding spaces don't matter
    ],
)
def test_skill_matches_by_name_or_label(typed):
    benchmark = [skill('Structured query language SQL', 1.0)]
    assert software_score({typed: 'expert'}, benchmark) == 100.0


@pytest.mark.parametrize(
    ('typed', 'benchmark_name'),
    [
        ('Microsoft', 'Microsoft Excel'),  # no partial matches
        ('Java', 'JavaScript'),
        ('C', 'C++'),
        ('Git', 'GitHub'),
    ],
)
def test_no_partial_matches(typed, benchmark_name):
    assert software_score({typed: 'expert'}, [skill(benchmark_name, 1.0)]) == 0.0


def test_best_level_wins_when_name_and_label_both_listed():
    student = {'SQL': 'beginner', 'Structured query language SQL': 'advanced'}
    assert software_score(student, [skill('Structured query language SQL', 1.0)]) == 75.0


def test_skills_outside_the_benchmark_dont_count():
    assert software_score({'Fortran': 'expert'}, [skill('Git', 1.0)]) == 0.0


# --- Scoring against a benchmark ---


def test_dimension_weights_are_each_types_share_of_the_benchmark():
    benchmark = [skill('Git', 0.8), skill('Python', 0.4), skill('Programming', 0.8, 'transferable')]
    _, weights, _ = score_against_benchmark({}, benchmark)

    assert weights == pytest.approx({'software': 0.6, 'transferable': 0.4})
    assert sum(weights.values()) == pytest.approx(1.0)


def test_heavier_skills_count_for_more():
    benchmark = [skill('Git', 0.8), skill('Fortran', 0.2)]

    assert software_score({'Git': 'expert'}, benchmark) == 80.0
    assert software_score({'Fortran': 'expert'}, benchmark) == 20.0


def test_skill_details_show_label_and_level_sorted_by_demand():
    benchmark = [skill('Docker', 0.3), skill('Structured query language SQL', 0.8)]
    _, _, details = score_against_benchmark({'SQL': 'advanced'}, benchmark)

    assert details['software'] == [
        {
            'name': 'Structured query language SQL',
            'label': 'SQL',
            'demand': 0.8,
            'your_level': 3,
            'met': False,
        },
        {'name': 'Docker', 'label': 'Docker', 'demand': 0.3, 'your_level': None, 'met': False},
    ]


def test_flagged_gaps_ranked_by_points_available_not_raw_gap():
    benchmark = [
        skill('Git', 0.9),
        skill('Python', 0.9),
        skill('Critical Thinking', 0.2, 'essential'),
    ]
    # software: 50% met, weight 0.9 -> 45 points available
    # essential: 0% met (bigger raw gap), weight 0.1 -> 10 points available
    result = readiness({'Git': 'expert'}, benchmark)

    assert [g['dimension'] for g in result['flagged_gaps']] == ['software', 'essential']
    assert result['flagged_gaps'][0]['points_available'] == 45.0
    assert result['flagged_gaps'][0]['top_unmet_skills'][0]['name'] == 'Python'
    assert result['overall_readiness_score'] == 45.0


def test_fully_met_benchmark_scores_100_with_no_gaps():
    result = readiness({'Git': 'expert'}, [skill('Git', 1.0)])
    assert result['overall_readiness_score'] == 100.0
    assert result['flagged_gaps'] == []


def test_empty_benchmark_scores_zero_without_crashing():
    result = readiness({'Git': 'expert'}, [])
    assert result['overall_readiness_score'] == 0.0
    assert result['flagged_gaps'] == []


def test_top_unmet_skills_lead_with_the_biggest_gain():
    # Has SQL at advanced (25% of 0.35 left = 0.0875) but lacks C# (all of 0.16)
    benchmark = [skill('Structured query language SQL', 0.35), skill('C#', 0.16)]
    result = readiness({'Structured query language SQL': 'advanced'}, benchmark)

    unmet = [s['name'] for s in result['flagged_gaps'][0]['top_unmet_skills']]
    assert unmet == ['C#', 'Structured query language SQL']


# --- skill groups (score_groups) ---


def group(key, tools, weight=1.0):
    return SkillGroup(key=key, name=key.title(), tools=tuple(tools), weight=weight)


def test_group_earns_credit_of_the_best_tool():
    frontend = group('frontend', ['React', 'Google Angular'])

    points, [detail] = score_groups(
        {'React': 'beginner', 'Google Angular': 'advanced'}, [frontend], points=50
    )

    assert points == 37.5  # advanced = 3/4 of 50
    assert detail['best_tool'] == 'Angular'
    assert detail['level'] == 'advanced'


def test_second_tool_in_a_group_adds_nothing():
    frontend = group('frontend', ['React', 'Google Angular'])
    one, _ = score_groups({'React': 'expert'}, [frontend])
    both, _ = score_groups({'React': 'expert', 'Google Angular': 'expert'}, [frontend])
    assert one == both == 100.0


def test_groups_split_points_by_weight():
    groups = [group('language', ['Python'], 0.75), group('cloud', ['AWS'], 0.25)]

    _, details = score_groups({}, groups, points=50)

    assert [d['out_of'] for d in details] == [37.5, 12.5]
    assert all(d['points'] == 0 and d['best_tool'] is None for d in details)


@pytest.mark.parametrize('typed', ['Structured query language SQL', 'SQL', '  sql '])
def test_group_tool_matches_by_name_or_label(typed):
    databases = group('databases', ['Structured query language SQL'])
    assert score_groups({typed: 'expert'}, [databases])[0] == 100.0


def test_level_credit_can_be_swapped_out():
    def three_levels(text):
        return text.title(), {'beginner': 0.25, 'intermediate': 0.6, 'expert': 1.0}[text]

    points, _ = score_groups(
        {'Python': 'intermediate'}, [group('language', ['Python'])], level_credit=three_levels
    )
    assert points == 60.0


def test_singleton_groups_score_like_ungrouped_skills():
    """One group per skill is exactly score_against_benchmark's math, so the
    two scoring paths can't drift apart."""
    skills = [
        BenchmarkSkill('Python', 'software', 0.8),
        BenchmarkSkill('Git', 'software', 0.5),
        BenchmarkSkill('Linux', 'software', 0.2),
    ]
    student = {'Python': 'advanced', 'git': 'beginner'}

    profile, _, _ = score_against_benchmark(student, skills)
    points, _ = score_groups(student, singleton_groups(skills), points=100)

    assert points == pytest.approx(profile['software'], abs=0.01)
