from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import CommandError, call_command

from .. import roles
from ..factories import RoleFactory, UserFactory
from ..management.commands import make_admin as make_admin_command
from .helpers import PASSWORD

User = get_user_model()


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


# --create
def answer_getpass(monkeypatch, *answers):
    replies = iter(answers)
    monkeypatch.setattr(make_admin_command.getpass, 'getpass', lambda prompt='': next(replies))


def create_admin(email):
    out = StringIO()
    call_command('make_admin', email, '--create', stdout=out)
    return out.getvalue()


@pytest.mark.django_db
def test_create_makes_verified_admin(monkeypatch):
    answer_getpass(monkeypatch, PASSWORD, PASSWORD)

    output = create_admin('new.admin@example.com')

    user = User.objects.get(email='new.admin@example.com')
    assert user.role.role_name == roles.ADMIN
    assert user.email_verified
    assert not user.is_staff
    assert not user.is_superuser
    assert user.check_password(PASSWORD)
    assert 'Created admin new.admin@example.com.' in output


@pytest.mark.django_db
def test_create_mismatched_passwords_error(monkeypatch):
    answer_getpass(monkeypatch, PASSWORD, PASSWORD + 'x')

    with pytest.raises(CommandError, match="don't match"):
        create_admin('new.admin@example.com')

    assert not User.objects.filter(email='new.admin@example.com').exists()


@pytest.mark.django_db
def test_create_weak_password_errors(monkeypatch):
    answer_getpass(monkeypatch, 'abc', 'abc')

    with pytest.raises(CommandError, match='too short'):
        create_admin('new.admin@example.com')

    assert not User.objects.filter(email='new.admin@example.com').exists()


@pytest.mark.django_db
def test_create_existing_email_errors(monkeypatch):
    user = UserFactory(email='ada@example.com')
    answer_getpass(monkeypatch, PASSWORD, PASSWORD)

    with pytest.raises(CommandError, match='without --create'):
        create_admin('Ada@Example.com')

    assert role_of(user) == roles.STUDENT
    assert User.objects.count() == 1


@pytest.mark.django_db
def test_create_invalid_email_errors(monkeypatch):
    answer_getpass(monkeypatch, PASSWORD, PASSWORD)

    with pytest.raises(CommandError, match='not a valid email'):
        create_admin('not-an-email')

    assert not User.objects.exists()
