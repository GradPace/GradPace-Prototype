# backend/benchmarks/tests/test_relevance.py

import pytest
from benchmarks.job_benchmark import BenchmarkSkill
from benchmarks.relevance import calculate_student_gaps, score_resource_relevance


def test_gap_calculation():
    benchmark_skills = [
        BenchmarkSkill(name='Python', skill_type='software', weight=0.8),
        BenchmarkSkill(name='SQL', skill_type='software', weight=0.6),
        BenchmarkSkill(name='Git', skill_type='transferable', weight=0.4),
    ]

    # Student has Python at advanced (75% credit) and Git at beginner (25% credit), missing SQL
    student_skills = {'Python': 'advanced', 'Git': 'beginner'}

    gaps = calculate_student_gaps(student_skills, benchmark_skills)

    # Python gap = 0.8 * (1 - 0.75) = 0.2
    # SQL gap = 0.6 * (1 - 0.0) = 0.6
    # Git gap = 0.4 * (1 - 0.25) = 0.3
    assert gaps['Python'] == 0.2
    assert gaps['SQL'] == 0.6
    assert gaps['Git'] == 0.3


def test_resource_relevance_scoring():
    student_gaps = {'Python': 0.2, 'SQL': 0.6, 'Git': 0.3}

    # Resource 1 covers SQL and Python
    res1_skills = ['SQL', 'Python']
    score1 = score_resource_relevance(res1_skills, student_gaps)

    # Resource 2 only covers Git
    res2_skills = ['Git']
    score2 = score_resource_relevance(res2_skills, student_gaps)

    # Res 1 covers (0.6 + 0.2) / 1.1 = ~72.7% of total gaps
    # Res 2 covers (0.3) / 1.1 = ~27.3% of total gaps
    assert score1['relevance_score'] > score2['relevance_score']
    assert 'SQL' in score1['matched_gaps']
