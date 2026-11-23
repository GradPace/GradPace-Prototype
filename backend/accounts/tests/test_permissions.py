import pytest
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from .. import roles
from ..factories import RoleFactory, UserFactory
from ..permissions import IsAdmin


def allowed(user):
    request = RequestFactory().get('/')
    request.user = user
    return IsAdmin().has_permission(request, view=None)


@pytest.mark.django_db
def test_admin_is_allowed():
    user = UserFactory(role=RoleFactory(role_name=roles.ADMIN))

    assert allowed(user)


@pytest.mark.django_db
@pytest.mark.parametrize('role', [roles.STUDENT, roles.ALUMNI, None])
def test_other_roles_are_blocked(role):
    user = UserFactory(role=RoleFactory(role_name=role) if role else None)

    assert not allowed(user)


def test_unauthenticated_is_blocked():
    assert not allowed(AnonymousUser())
