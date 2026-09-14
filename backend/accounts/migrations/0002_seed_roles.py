from django.db import migrations

ROLES = [
    ('student', 'A currently-enrolled student'),
    ('alumni', 'A graduated student'),
    ('admin', 'Staff who manage GradPace itself - not a Django superuser'),
]


def seed_roles(apps, schema_editor):
    Role = apps.get_model('accounts', 'Role')
    for role_name, description in ROLES:
        Role.objects.get_or_create(role_name=role_name, defaults={'description': description})


def unseed_roles(apps, schema_editor):
    Role = apps.get_model('accounts', 'Role')
    Role.objects.filter(role_name__in=[name for name, _ in ROLES]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_roles, unseed_roles),
    ]
