"""Building a job's benchmark from its postings (job_benchmark.py)."""

import pytest

from intelligence.factories import JobFactory, JobPostingFactory, JobSkillFactory

from .. import job_benchmark
from ..job_benchmark import build_job_benchmark, get_job


def weights(benchmark):
    return {s.name: s.weight for s in benchmark.skills}


@pytest.fixture
def small_threshold(monkeypatch):
    """Lets a test use intern/entry postings without creating 10 of them."""
    monkeypatch.setattr(job_benchmark, 'MIN_STUDENT_POSTINGS', 2)


@pytest.mark.django_db
def test_weight_is_share_of_postings_listing_the_skill(small_threshold):
    job = JobFactory()
    git = JobSkillFactory(job=job, name='Git', skill_type='software')
    python = JobSkillFactory(job=job, name='Python', skill_type='software')
    JobPostingFactory(job=job, seniority='entry', skills=[git, python])
    JobPostingFactory(job=job, seniority='intern', skills=[git])

    benchmark = build_job_benchmark(job)

    assert weights(benchmark) == {'Git': 1.0, 'Python': 0.5}
    assert benchmark.postings_used == 2
    assert benchmark.seniorities_used == 'intern/entry'


@pytest.mark.django_db
def test_uses_only_intern_and_entry_postings_when_there_are_enough(small_threshold):
    job = JobFactory()
    git = JobSkillFactory(job=job, name='Git', skill_type='software')
    kubernetes = JobSkillFactory(job=job, name='Kubernetes', skill_type='software')
    JobPostingFactory(job=job, seniority='entry', skills=[git])
    JobPostingFactory(job=job, seniority='intern', skills=[git])
    JobPostingFactory(job=job, seniority='senior', skills=[kubernetes])

    assert weights(build_job_benchmark(job)) == {'Git': 1.0}


@pytest.mark.django_db
def test_falls_back_to_all_postings_when_too_few_are_entry_level():
    # 1 entry posting is below MIN_STUDENT_POSTINGS (10), so all 4 are used
    job = JobFactory()
    git = JobSkillFactory(job=job, name='Git', skill_type='software')
    kubernetes = JobSkillFactory(job=job, name='Kubernetes', skill_type='software')
    JobPostingFactory(job=job, seniority='entry', skills=[git])
    for _ in range(3):
        JobPostingFactory(job=job, seniority='senior', skills=[git, kubernetes])

    benchmark = build_job_benchmark(job)

    assert weights(benchmark) == {'Git': 1.0, 'Kubernetes': 0.75}
    assert benchmark.seniorities_used == 'all'


@pytest.mark.django_db
def test_rare_skills_are_left_out():
    job = JobFactory()
    git = JobSkillFactory(job=job, name='Git', skill_type='software')
    rare = JobSkillFactory(job=job, name='Fortran', skill_type='software')
    for _ in range(10):
        JobPostingFactory(job=job, seniority='mid', skills=[git])
    JobPostingFactory(job=job, seniority='mid', skills=[git, rare])  # 1 of 11 < 10%

    assert 'Fortran' not in weights(build_job_benchmark(job))


@pytest.mark.django_db
def test_sorted_most_in_demand_first(small_threshold):
    job = JobFactory()
    a = JobSkillFactory(job=job, name='A', skill_type='software')
    b = JobSkillFactory(job=job, name='B', skill_type='software')
    JobPostingFactory(job=job, seniority='entry', skills=[a, b])
    JobPostingFactory(job=job, seniority='entry', skills=[b])

    assert [s.name for s in build_job_benchmark(job).skills] == ['B', 'A']


@pytest.mark.django_db
def test_no_postings_falls_back_to_the_jobs_onet_skills():
    job = JobFactory()
    JobSkillFactory(job=job, name='Git', skill_type='software')

    benchmark = build_job_benchmark(job)

    assert weights(benchmark) == {'Git': 1.0}
    assert benchmark.postings_used == 0


@pytest.mark.django_db
def test_get_job_prefers_the_national_row():
    JobFactory(soc_code='15-1252', area='Norfolk, VA')
    national = JobFactory(soc_code='15-1252', area='National')

    assert get_job('15-1252') == national
    assert get_job('99-9999') is None
