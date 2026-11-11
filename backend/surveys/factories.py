import factory

from accounts.factories import RoleFactory, UserFactory

from .models import AlumniSurveyResponse


class AlumniUserFactory(UserFactory):
    role = factory.SubFactory(RoleFactory, role_name='alumni')


class AlumniSurveyResponseFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = AlumniSurveyResponse

    user = factory.SubFactory(AlumniUserFactory)
    current_job_title = 'Software Engineer'
    industry = 'software'
    # Not checked against the catalog here. The model doesn't validate it,
    # only the API serializer does.
    top_skills = factory.LazyFunction(lambda: ['Python'])
    preparedness_rating = 4
    platform_helpfulness_rating = 4
    suggested_skills = factory.LazyFunction(lambda: ['Rust'])
    platform_feedback = 'Helped me find my gaps before graduating.'
