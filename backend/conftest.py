import pytest
from django.core.cache import cache


@pytest.fixture(autouse=True)
def _clear_cache():
    """The auth throttles (DEFAULT_THROTTLE_RATES) count requests in the
    cache - start every test with fresh counts so they don't add up across
    the suite."""
    cache.clear()
