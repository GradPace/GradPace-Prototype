import pytest
from django.core.management import call_command

from intelligence.models import Job


@pytest.fixture(autouse=True)
def _unseeded_catalog(db):
    """The intelligence app's migrations seed the 24 BLS jobs and 400 postings,
    but most of these tests build their own small jobs so the expected numbers
    are easy to check by hand. Skills and postings cascade; the delete rolls
    back with the test. Same approach as intelligence/tests/conftest.py."""
    Job.objects.all().delete()


@pytest.fixture
def real_catalog(_unseeded_catalog):
    """The real seed data, for tests that need it (e.g. the demo students).
    Runs after _unseeded_catalog, so it reloads what that cleared."""
    call_command('seed_jobs', verbosity=0)
