import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError

from ..admin import JobPostingAdminForm
from ..factories import JobFactory, JobPostingFactory, JobSkillFactory
from ..models import JobPosting


@pytest.mark.django_db
def test_create_posting_with_skills():
    job = JobFactory()
    python = JobSkillFactory(job=job, name='Python', skill_type='software', importance=None)
    sql = JobSkillFactory(job=job, name='SQL', skill_type='software', importance=None)

    posting = JobPostingFactory(job=job, skills=[python, sql])

    assert list(job.postings.all()) == [posting]
    assert set(posting.skills.all()) == {python, sql}
    assert list(python.postings.all()) == [posting]


@pytest.mark.django_db
def test_set_skills_rejects_another_jobs_skill():
    posting = JobPostingFactory()
    own = JobSkillFactory(job=posting.job, name='Python')
    other = JobSkillFactory(job=JobFactory(), name='Excel')

    with pytest.raises(ValidationError) as excinfo:
        posting.set_skills([own, other])

    assert 'skills' in excinfo.value.message_dict
    assert posting.skills.count() == 0


@pytest.mark.django_db
def test_clean_rejects_another_jobs_skill_added_directly():
    posting = JobPostingFactory()
    posting.skills.add(JobSkillFactory(job=JobFactory(), name='Excel'))

    with pytest.raises(ValidationError) as excinfo:
        posting.full_clean()
    assert 'skills' in excinfo.value.message_dict


@pytest.mark.django_db
def test_admin_form_rejects_another_jobs_skill():
    job = JobFactory()
    other = JobSkillFactory(job=JobFactory(), name='Excel')
    form = JobPostingAdminForm(
        data={
            'job': job.pk,
            'title': 'Junior Software Developer',
            'company': 'Acme Corp',
            'location': 'Remote',
            'seniority': 'entry',
            'description': 'Build things.',
            'source': 'generated',
            'skills': [other.pk],
        }
    )

    assert not form.is_valid()
    assert 'skills' in form.errors


@pytest.mark.django_db
def test_salary_min_above_max_rejected_by_clean():
    posting = JobPostingFactory.build(job=JobFactory(), salary_min=90000, salary_max=70000)

    with pytest.raises(ValidationError) as excinfo:
        posting.full_clean()
    assert 'salary_max' in excinfo.value.message_dict


@pytest.mark.django_db
@pytest.mark.parametrize(
    ('salary_min', 'salary_max'),
    [(80000, 80000), (None, 80000), (80000, None), (None, None)],
)
def test_salary_equal_or_missing_allowed(salary_min, salary_max):
    posting = JobPostingFactory.build(
        job=JobFactory(), salary_min=salary_min, salary_max=salary_max
    )

    posting.full_clean()


@pytest.mark.django_db
def test_salary_min_above_max_rejected_by_database():
    with pytest.raises(IntegrityError):
        JobPostingFactory(salary_min=90000, salary_max=70000)


@pytest.mark.django_db
def test_seniority_rejects_unknown_value():
    posting = JobPostingFactory.build(job=JobFactory(), seniority='principal')

    with pytest.raises(ValidationError) as excinfo:
        posting.full_clean()
    assert 'seniority' in excinfo.value.message_dict


@pytest.mark.django_db
def test_deleting_job_deletes_postings():
    posting = JobPostingFactory()

    posting.job.delete()

    assert not JobPosting.objects.filter(pk=posting.pk).exists()
