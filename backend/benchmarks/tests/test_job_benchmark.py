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


# --- location filter ---


@pytest.mark.django_db
def test_location_limits_postings_to_that_location():
    job = JobFactory()
    git = JobSkillFactory(job=job, name='Git', skill_type='software')
    kubernetes = JobSkillFactory(job=job, name='Kubernetes', skill_type='software')
    JobPostingFactory(job=job, location='Norfolk, VA', skills=[git])
    JobPostingFactory(job=job, location='Austin, TX', skills=[kubernetes])

    benchmark = build_job_benchmark(job, location='Norfolk, VA')

    assert weights(benchmark) == {'Git': 1.0}
    assert benchmark.postings_used == 1


@pytest.mark.django_db
def test_no_location_uses_every_posting():
    job = JobFactory()
    git = JobSkillFactory(job=job, name='Git', skill_type='software')
    JobPostingFactory(job=job, location='Norfolk, VA', skills=[git])
    JobPostingFactory(job=job, location='Austin, TX', skills=[])

    assert build_job_benchmark(job).postings_used == 2


@pytest.mark.django_db
def test_location_with_no_postings_falls_back_to_the_job_skill_list():
    job = JobFactory()
    JobSkillFactory(job=job, name='Git', skill_type='software')
    JobPostingFactory(job=job, location='Austin, TX')

    benchmark = build_job_benchmark(job, location='Norfolk, VA')

    assert weights(benchmark) == {'Git': 1.0}
    assert benchmark.postings_used == 0


# --- skill groups ---

CLOUD = ('cloud', 'Cloud', ['Amazon Web Services AWS software', 'Microsoft Azure software'])


@pytest.mark.django_db
def test_group_weight_is_share_of_postings_listing_any_tool():
    job = JobFactory()
    aws = JobSkillFactory(job=job, name='Amazon Web Services AWS software')
    azure = JobSkillFactory(job=job, name='Microsoft Azure software')
    git = JobSkillFactory(job=job, name='Git')
    JobPostingFactory(job=job, skills=[aws])
    JobPostingFactory(job=job, skills=[azure])
    JobPostingFactory(job=job, skills=[aws, azure])  # counts once
    JobPostingFactory(job=job, skills=[git])

    benchmark = build_job_benchmark(job, skill_groups=[CLOUD])

    [group] = benchmark.groups
    assert (group.key, group.name) == ('cloud', 'Cloud')
    assert group.tools == (
        'Amazon Web Services AWS software',
        'Microsoft Azure software',
    )
    assert group.weight == 0.75


@pytest.mark.django_db
def test_groups_are_not_cut_off_by_min_demand():
    job = JobFactory()
    rare = JobSkillFactory(job=job, name='Rare Tool')
    JobPostingFactory(job=job, skills=[rare])
    for _ in range(19):
        JobPostingFactory(job=job, skills=[])

    benchmark = build_job_benchmark(job, skill_groups=[('rare', 'Rare', ['Rare Tool'])])

    assert weights(benchmark) == {}  # 5% < MIN_DEMAND
    assert benchmark.groups[0].weight == 0.05


@pytest.mark.django_db
def test_groups_weigh_equally_without_postings():
    job = JobFactory()

    benchmark = build_job_benchmark(job, skill_groups=[CLOUD, ('os', 'OS', ['Linux'])])

    assert [g.weight for g in benchmark.groups] == [1.0, 1.0]


@pytest.mark.django_db
def test_groups_follow_the_location_filter():
    job = JobFactory()
    aws = JobSkillFactory(job=job, name='Amazon Web Services AWS software')
    JobPostingFactory(job=job, location='Norfolk, VA', skills=[aws])
    JobPostingFactory(job=job, location='Austin, TX', skills=[])

    benchmark = build_job_benchmark(job, location='Norfolk, VA', skill_groups=[CLOUD])

    assert benchmark.groups[0].weight == 1.0


@pytest.mark.django_db
def test_no_skill_groups_leaves_groups_empty():
    job = JobFactory()
    JobPostingFactory(job=job)

    assert build_job_benchmark(job).groups == []
