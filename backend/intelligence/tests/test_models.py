import pytest
from django.db import IntegrityError

from ..factories import JobFactory
from ..models import Job, JobSkill


@pytest.mark.django_db
def test_create_job_with_skills():
    job = Job.objects.create(
        title='Software Developers',
        soc_code='15-1252',
        description='Research, design, and develop computer software.',
        area='National',
        median_annual_wage=133080,
        employment=1656880,
        source='official',
    )
    JobSkill.objects.create(job=job, name='Programming', importance=4.12)
    JobSkill.objects.create(job=job, name='Critical Thinking', importance=None)

    job.refresh_from_db()
    assert job.skills.count() == 2
    assert set(job.skills.values_list('name', flat=True)) == {'Programming', 'Critical Thinking'}
    assert job.skills.get(name='Programming').importance == 4.12
    assert job.skills.get(name='Critical Thinking').importance is None
    assert Job.objects.get(soc_code='15-1252') == job


@pytest.mark.django_db
def test_job_wage_and_employment_are_nullable():
    job = JobFactory(source='generated', median_annual_wage=None, employment=None)

    job.refresh_from_db()
    assert job.median_annual_wage is None
    assert job.employment is None


@pytest.mark.django_db
def test_duplicate_skill_name_rejected():
    job = JobFactory()
    JobSkill.objects.create(job=job, name='Python')

    with pytest.raises(IntegrityError):
        JobSkill.objects.create(job=job, name='Python')


@pytest.mark.django_db
def test_same_skill_name_allowed_on_different_jobs():
    JobSkill.objects.create(job=JobFactory(), name='Python')
    JobSkill.objects.create(job=JobFactory(), name='Python')

    assert JobSkill.objects.filter(name='Python').count() == 2
