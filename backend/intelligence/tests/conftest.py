import pytest

from ..models import Job


@pytest.fixture(autouse=True)
def _unseeded_catalog(db):
    """Migrations 0004/0005 seed the jobs and postings, but these tests assume an
    empty catalog. Skills and postings cascade; the delete rolls back with the test."""
    Job.objects.all().delete()
