import factory
from django.contrib.auth import get_user_model

User = get_user_model()

DEFAULT_PASSWORD = "Zq7!fWbn2"  # satisfies AUTH_PASSWORD_VALIDATORS - see accounts/validators.py


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User
        django_get_or_create = ("username",)
        skip_postgeneration_save = True

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda o: f"{o.username}@example.com")

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        self.set_password(extracted or DEFAULT_PASSWORD)
        if create:
            self.save()
