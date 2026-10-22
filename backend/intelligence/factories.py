import factory

from .models import Job, JobPosting, JobSkill


class JobFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Job

    title = 'Software Developer'
    soc_code = factory.Sequence(lambda n: f'15-{n:04d}')
    area = 'National'
    source = 'official'


class JobSkillFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = JobSkill
        django_get_or_create = ('job', 'name')

    job = factory.SubFactory(JobFactory)
    name = factory.Sequence(lambda n: f'Skill {n}')
    skill_type = 'essential'
    importance = 3.5


class JobPostingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = JobPosting
        skip_postgeneration_save = True

    job = factory.SubFactory(JobFactory)
    title = 'Junior Software Developer'
    company = 'Acme Corp'
    location = 'Norfolk, VA'
    seniority = 'entry'
    salary_min = 70000
    salary_max = 90000
    description = 'Build and maintain web applications with a small team.'
    source = 'generated'

    @factory.post_generation
    def skills(self, create, extracted, **kwargs):
        if create and extracted:
            self.set_skills(extracted)
