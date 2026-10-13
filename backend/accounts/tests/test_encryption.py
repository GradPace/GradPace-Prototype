"""Encryption at rest (accounts/fields.py, migration 0005)."""

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from ..factories import (
    CertificateFactory,
    StudentProfileFactory,
    TakenClassFactory,
    UserFactory,
)
from .helpers import login

# Every encrypted field, with a value to round-trip through it.
ENCRYPTED_FIELDS = [
    (UserFactory, 'first_name', 'Ada'),
    (UserFactory, 'last_name', 'Lovelace'),
    (StudentProfileFactory, 'major', 'Mathematics'),
    (StudentProfileFactory, 'uni', 'University of London'),
    (StudentProfileFactory, 'location', 'London'),
    (TakenClassFactory, 'grade', 'A-'),
    (CertificateFactory, 'credential_url', 'https://example.com/credential/123'),
]

# Every Fernet token starts with this (base64 of its version byte + timestamp).
FERNET_PREFIX = 'gAAAAA'


def raw_value(model, pk, field_name):
    """The column's contents as stored, bypassing the field's decryption."""
    qn = connection.ops.quote_name
    pk_field = model._meta.pk
    with connection.cursor() as cursor:
        cursor.execute(
            f'SELECT {qn(model._meta.get_field(field_name).column)} '
            f'FROM {qn(model._meta.db_table)} WHERE {qn(pk_field.column)} = %s',
            [pk_field.get_db_prep_value(pk, connection)],
        )
        return cursor.fetchone()[0]


@pytest.mark.django_db
@pytest.mark.parametrize(('factory', 'field_name', 'value'), ENCRYPTED_FIELDS)
def test_value_round_trips(factory, field_name, value):
    obj = factory(**{field_name: value})

    obj.refresh_from_db()

    assert getattr(obj, field_name) == value


@pytest.mark.django_db
@pytest.mark.parametrize(('factory', 'field_name', 'value'), ENCRYPTED_FIELDS)
def test_column_holds_ciphertext(factory, field_name, value):
    obj = factory(**{field_name: value})

    stored = raw_value(type(obj), obj.pk, field_name)

    assert stored.startswith(FERNET_PREFIX)
    assert value not in stored


@pytest.mark.django_db
def test_same_value_encrypts_differently():
    """Why these fields can't be filtered on: the ciphertext for a value is
    different every time, so filter(major=...) never matches."""
    first = StudentProfileFactory(major='Physics')
    second = StudentProfileFactory(major='Physics')

    first_stored = raw_value(type(first), first.pk, 'major')
    second_stored = raw_value(type(second), second.pk, 'major')

    assert first_stored != second_stored


@pytest.mark.django_db
def test_blank_is_stored_blank():
    """Upstream would store '' as NULL, which the NOT NULL columns reject."""
    profile = StudentProfileFactory(location='')

    profile.refresh_from_db()

    assert profile.location == ''
    assert raw_value(type(profile), profile.pk, 'location') == ''


@pytest.mark.django_db
def test_credential_url_is_still_validated_as_a_url(client):
    """credential_url used to be a URLField - its validator moved onto the
    encrypted field, so the API still rejects a non-URL."""
    profile = StudentProfileFactory()
    tokens = login(client, profile.user)

    response = client.post(
        '/api/auth/profile/certificates/',
        {
            'name': 'AWS Certified Cloud Practitioner',
            'issuing_organization': 'Amazon Web Services',
            'credential_url': 'not-a-url',
        },
        content_type='application/json',
        HTTP_AUTHORIZATION=f'Bearer {tokens["access"]}',
    )

    assert response.status_code == 400
    assert 'credential_url' in response.json()


BEFORE = [('accounts', '0004_customuser_unique_email_ci')]
AFTER = [('accounts', '0005_encrypt_sensitive_fields')]


def migrate_to(targets):
    executor = MigrationExecutor(connection)
    executor.loader.build_graph()
    executor.migrate(targets)
    return executor.loader.project_state(targets).apps


@pytest.mark.django_db(transaction=True)
def test_migration_encrypts_existing_rows_and_reverses():
    try:
        old_apps = migrate_to(BEFORE)
        user = old_apps.get_model('accounts', 'CustomUser').objects.create(
            email='ada@example.com', password='!', first_name='Ada', last_name=''
        )
        profile = old_apps.get_model('accounts', 'StudentProfile').objects.create(
            user=user, student_id='S1234567', major='Mathematics', uni='UCL', location='London'
        )
        updated_at = profile.updated_at

        new_apps = migrate_to(AFTER)
        CustomUser = new_apps.get_model('accounts', 'CustomUser')
        StudentProfile = new_apps.get_model('accounts', 'StudentProfile')

        assert raw_value(CustomUser, user.pk, 'first_name').startswith(FERNET_PREFIX)
        assert raw_value(CustomUser, user.pk, 'last_name') == ''
        assert raw_value(StudentProfile, profile.pk, 'major').startswith(FERNET_PREFIX)
        migrated = StudentProfile.objects.get(pk=profile.pk)
        assert (migrated.major, migrated.uni, migrated.location) == ('Mathematics', 'UCL', 'London')
        assert migrated.updated_at == updated_at
        assert CustomUser.objects.get(pk=user.pk).first_name == 'Ada'

        migrate_to(BEFORE)

        assert raw_value(CustomUser, user.pk, 'first_name') == 'Ada'
        assert raw_value(StudentProfile, profile.pk, 'major') == 'Mathematics'
    finally:
        # Leave the schema at the latest migration for the tests that follow.
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
