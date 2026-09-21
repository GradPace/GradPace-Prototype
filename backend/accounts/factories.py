import factory
from django.contrib.auth import get_user_model

from .models import Certificate, Role, Skill, StudentProfile, TakenClass

User = get_user_model()

DEFAULT_PASSWORD = 'Zq7!fWbn2'  # satisfies AUTH_PASSWORD_VALIDATORS - see accounts/validators.py


class RoleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Role
        django_get_or_create = ('role_name',)

    role_name = 'student'


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ('email',)
        skip_postgeneration_save = True

    email = factory.Sequence(lambda n: f'user{n}@example.com')
    first_name = 'Test'
    last_name = 'User'
    role = factory.SubFactory(RoleFactory)

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        self.set_password(extracted or DEFAULT_PASSWORD)
        if create:
            self.save()


class StudentProfileFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = StudentProfile
        django_get_or_create = ('student_id',)

    user = factory.SubFactory(UserFactory)
    student_id = factory.Sequence(lambda n: f'S{n:07d}')
    major = 'Computer Science'
    uni = 'State University'


class TakenClassFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TakenClass

    student = factory.SubFactory(StudentProfileFactory)
    course_code = factory.Sequence(lambda n: f'CS{n:03d}')
    course_name = 'Intro to Software Engineering'
    semester = 'fall'
    year = 2025
    grade = 'A'


class CertificateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Certificate

    student = factory.SubFactory(StudentProfileFactory)
    name = 'AWS Certified Cloud Practitioner'
    issuing_organization = 'Amazon Web Services'


class SkillFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Skill
        django_get_or_create = ('student', 'name')

    student = factory.SubFactory(StudentProfileFactory)
    name = factory.Sequence(lambda n: f'Skill {n}')
    proficiency_level = 'intermediate'
