from io import StringIO

import pytest
from django.core.management import CommandError, call_command

from .. import roles
from ..factories import RoleFactory, UserFactory


def make_admin(email):
    out = StringIO()
    call_command('make_admin', email, stdout=out)
    return out.getvalue()


def role_of(user):
    user.refresh_from_db()
    return user.role.role_name if user.role else None


@pytest.mark.django_db
def test_sets_admin_role():
    user = UserFactory(email='ada@example.com')

    output = make_admin('ada@example.com')

    assert role_of(user) == roles.ADMIN
    assert not user.is_staff
    assert not user.is_superuser
    assert 'ada@example.com is now an admin.' in output


@pytest.mark.django_db
def test_email_is_case_insensitive():
    user = UserFactory(email='ada@example.com')

    make_admin('Ada@Example.com')

    assert role_of(user) == roles.ADMIN


@pytest.mark.django_db
def test_unknown_email_errors():
    user = UserFactory(email='ada@example.com')

    with pytest.raises(CommandError, match='No user with email nobody@example.com'):
        make_admin('nobody@example.com')

    assert role_of(user) == roles.STUDENT


@pytest.mark.django_db
def test_already_admin_is_a_no_op():
    user = UserFactory(email='ada@example.com', role=RoleFactory(role_name=roles.ADMIN))

    output = make_admin('ada@example.com')

    assert role_of(user) == roles.ADMIN
    assert 'already an admin' in output
