import factory

from .models import Job, JobSkill


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
    importance = 3.5
