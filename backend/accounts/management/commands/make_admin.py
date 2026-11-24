import getpass

from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.core.validators import validate_email

from accounts import roles
from accounts.models import Role

User = get_user_model()


class Command(BaseCommand):
    help = (
        'Give an existing user the admin role, or with --create make a new admin account '
        "(email already verified, password asked for in the terminal). Doesn't set "
        'is_staff/is_superuser.'
    )

    def add_arguments(self, parser):
        parser.add_argument('email')
        # No password option on purpose: it would end up in shell history and
        # the process list. --create always asks for it with getpass.
        parser.add_argument(
            '--create',
            action='store_true',
            help='Create a new admin account for this email instead of promoting one.',
        )

    def handle(self, *args, **options):
        if options['create']:
            self._create(options['email'])
        else:
            self._promote(options['email'])

    def _promote(self, email):
        try:
            # Case-insensitive, like login (CustomUserManager.get_by_natural_key).
            user = User.objects.get_by_natural_key(email)
        except User.DoesNotExist:
            raise CommandError(f'No user with email {email}.') from None

        if user.role is not None and user.role.role_name == roles.ADMIN:
            self.stdout.write(f'{user.email} is already an admin.')
            return

        # Seeded by migration 0002_seed_roles.
        user.role = Role.objects.get(role_name=roles.ADMIN)
        user.save(update_fields=['role'])
        self.stdout.write(f'{user.email} is now an admin.')

    def _create(self, email):
        try:
            validate_email(email)
        except ValidationError:
            raise CommandError(f'{email} is not a valid email address.') from None
        # Same case-insensitive match as the unique_email_ci constraint.
        if User.objects.filter(email__lower=email.lower()).exists():
            raise CommandError(
                f'User {email} already exists. Run make_admin without --create to make it an admin.'
            )

        password = getpass.getpass('Password: ')
        if not password:
            raise CommandError('The password cannot be blank.')
        if password != getpass.getpass('Password (again): '):
            raise CommandError("The passwords don't match.")
        try:
            # The same validators as registration (AUTH_PASSWORD_VALIDATORS).
            password_validation.validate_password(password, user=User(email=email))
        except ValidationError as exc:
            raise CommandError(' '.join(exc.messages)) from None

        # Made from the command line by someone who controls the address, so
        # there's no verification link to send - same as createsuperuser.
        user = User.objects.create_user(
            email,
            password,
            role=Role.objects.get(role_name=roles.ADMIN),
            email_verified=True,
        )
        self.stdout.write(f'Created admin {user.email}.')
