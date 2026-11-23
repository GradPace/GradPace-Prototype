from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from accounts import roles
from accounts.models import Role

User = get_user_model()


class Command(BaseCommand):
    help = "Give an existing user the admin role. Doesn't change is_staff/is_superuser."

    def add_arguments(self, parser):
        parser.add_argument('email')

    def handle(self, *args, **options):
        email = options['email']
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
