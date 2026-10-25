"""Ranking a student's readiness across every job (best_fit.py)."""

import pytest

from accounts.factories import SkillFactory, StudentProfileFactory
from intelligence.factories import JobFactory, JobPostingFactory, JobSkillFactory

from .. import best_fit
from ..best_fit import best_fit_jobs


def job_wanting(title, soc_code, skill_names, postings=1):
    job = JobFactory(title=title, soc_code=soc_code)
    skills = [JobSkillFactory(job=job, name=n, skill_type='software') for n in skill_names]
    for _ in range(postings):
        JobPostingFactory(job=job, seniority='entry', skills=skills)
    return job


@pytest.mark.django_db
def test_well_supported_jobs_rank_above_limited_data_ones(monkeypatch):
    monkeypatch.setattr(best_fit, 'LIMITED_DATA_POSTINGS', 2)
    job_wanting('Thin Job', '15-0001', ['Git'], postings=1)  # limited, student scores 100
    job_wanting('Solid Job', '15-0002', ['Git', 'Python'], postings=2)  # student scores 50
    student = StudentProfileFactory()
    SkillFactory(student=student, name='Git', proficiency_level='expert')

    results = best_fit_jobs(student)

    assert [r['role']['title'] for r in results] == ['Solid Job', 'Thin Job']
    assert [r['limited_data'] for r in results] == [False, True]
    assert results[0]['overall_readiness_score'] == 50.0
    assert results[0]['top_unmet_skills'][0]['name'] == 'Python'


@pytest.mark.django_db
def test_same_student_fits_different_jobs_differently():
    job_wanting('Web Developers', '15-1254', ['JavaScript', 'React'])
    job_wanting('Database Administrators', '15-1242', ['Transact-SQL', 'Oracle Database'])
    student = StudentProfileFactory()
    SkillFactory(student=student, name='JavaScript', proficiency_level='advanced')
    SkillFactory(student=student, name='React', proficiency_level='advanced')

    scores = {r['role']['title']: r['overall_readiness_score'] for r in best_fit_jobs(student)}

    assert scores == {'Web Developers': 75.0, 'Database Administrators': 0.0}
