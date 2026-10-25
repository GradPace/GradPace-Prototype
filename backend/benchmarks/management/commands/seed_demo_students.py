"""Create a few demo students with skills and a target job, at different
readiness levels, for showing off the dashboard.

    uv run manage.py migrate              # also loads the BLS job data
    uv run manage.py seed_demo_students --password <something memorable>

Safe to rerun: each demo student is matched by email, and their skills and
target job are reset to the definitions below. Prints each student's login
and readiness score. Refuses to run with DEBUG off (i.e. production) unless
--allow-production is passed, since it creates accounts with a known
password.
"""

import secrets

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import Role, Skill, StudentProfile
from benchmarks.job_benchmark import get_job
from benchmarks.scoring import score_student

User = get_user_model()

# Every job has its own benchmark, but the demo centers on one role with
# strong data (51 intern/entry postings), one school and one location. Change
# DEMO_ROLE to demo a different job - any SOC code from /api/benchmark/roles/.
DEMO_ROLE = '15-1252'  # Software Developers

# Students at clearly different readiness levels, plus one (Jordan) who shows
# off best-fit jobs: aiming for Software Developers, but a far better Data
# Scientist. Skill names are exact O*NET names, as the skill picker saves them;
# levels are Skill.proficiency_level ('beginner' = 1 ... 'expert' = 4).
DEMO_STUDENTS = [
    {
        # Near graduation, internship experience - high readiness.
        'email': 'demo.alex@example.com',
        'first_name': 'Alex',
        'last_name': 'Rivera',
        'student_id': 'DEMO0001',
        'target_job': DEMO_ROLE,
        'skills': {
            'Programming': 'expert',
            'Git': 'expert',
            'Python': 'expert',
            'Structured query language SQL': 'advanced',
            'Docker': 'advanced',
            'Linux': 'advanced',
            'PostgreSQL': 'intermediate',
            'React': 'advanced',
            'RESTful API': 'advanced',
            'Amazon Web Services AWS software': 'intermediate',
            'GitHub': 'expert',
            'TypeScript': 'intermediate',
            'JavaScript': 'advanced',
            'Oracle Java': 'advanced',
            'Node.js': 'intermediate',
            'Critical Thinking': 'advanced',
        },
    },
    {
        # Mid-program - solid coursework skills, little tooling yet.
        'email': 'demo.priya@example.com',
        'first_name': 'Priya',
        'last_name': 'Shah',
        'student_id': 'DEMO0002',
        'target_job': DEMO_ROLE,
        'skills': {
            'Programming': 'advanced',
            'Python': 'advanced',
            'Git': 'intermediate',
            'Structured query language SQL': 'intermediate',
            'Oracle Java': 'intermediate',
            'C++': 'intermediate',
            'GitHub': 'intermediate',
            'Linux': 'beginner',
            'Critical Thinking': 'intermediate',
        },
    },
    {
        # Early in the program - just getting started.
        'email': 'demo.marcus@example.com',
        'first_name': 'Marcus',
        'last_name': 'Lee',
        'student_id': 'DEMO0003',
        'target_job': DEMO_ROLE,
        'skills': {
            'Programming': 'beginner',
            'Python': 'beginner',
            'Oracle Java': 'beginner',
            'Critical Thinking': 'beginner',
            # Not in the Software Developers benchmark - shows that skills
            # outside it don't count toward the score.
            'Microsoft Excel': 'intermediate',
        },
    },
    {
        # Strong in data and stats, light on software tooling - targets
        # Software Developers, but best-fit jobs ranks Data Scientists first.
        'email': 'demo.jordan@example.com',
        'first_name': 'Jordan',
        'last_name': 'Kim',
        'student_id': 'DEMO0004',
        'target_job': DEMO_ROLE,
        'skills': {
            'Python': 'advanced',
            'Structured query language SQL': 'advanced',
            'Mathematics': 'advanced',
            'pandas': 'intermediate',
            'Scikit-learn': 'intermediate',
            'Tableau': 'beginner',
            'R': 'beginner',
            'Git': 'beginner',
        },
    },
]
DEMO_MAJOR = 'Computer Science'
DEMO_UNI = 'Old Dominion University'
DEMO_LOCATION = 'Norfolk, VA'


class Command(BaseCommand):
    help = 'Create demo students with skills and a target job (dev/demo use only).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--password',
            help='Password for every demo account. Default: a random one, printed at the end.',
        )
        parser.add_argument(
            '--allow-production',
            action='store_true',
            help='Run even with DEBUG off. Creates real, loginable accounts.',
        )

    def handle(self, *args, **options):
        if not settings.DEBUG and not options['allow_production']:
            raise CommandError(
                'DEBUG is off - this looks like production. Pass --allow-production '
                'if you really want demo accounts here.'
            )

        jobs = {}
        for student in DEMO_STUDENTS:
            job = get_job(student['target_job'])
            if job is None:
                raise CommandError(
                    f'No job with SOC code {student["target_job"]} - run migrate first.'
                )
            jobs[student['email']] = job

        password = options['password'] or secrets.token_urlsafe(12)
        student_role = Role.objects.get(role_name='student')

        with transaction.atomic():
            results = [
                self.create_student(student, jobs[student['email']], password, student_role)
                for student in DEMO_STUDENTS
            ]

        self.stdout.write(self.style.SUCCESS(f'{len(results)} demo students ready.'))
        for email, job, score in results:
            self.stdout.write(f'  {email:<26} {job.title:<32} readiness {score:>6.2f}')
        if not options['password']:
            self.stdout.write(f'Password for all of them: {password}')

    def create_student(self, data, job, password, role):
        user, _ = User.objects.get_or_create(
            email=data['email'],
            defaults={
                'first_name': data['first_name'],
                'last_name': data['last_name'],
                'role': role,
            },
        )
        user.set_password(password)
        user.save()

        profile, _ = StudentProfile.objects.update_or_create(
            user=user,
            defaults={
                'student_id': data['student_id'],
                'major': DEMO_MAJOR,
                'uni': DEMO_UNI,
                'location': DEMO_LOCATION,
                'target_job': job,
            },
        )

        profile.skills.all().delete()
        Skill.objects.bulk_create(
            Skill(student=profile, name=name, proficiency_level=level)
            for name, level in data['skills'].items()
        )

        score = score_student(profile, job)['overall_readiness_score']
        profile.readiness_score = score
        profile.save(update_fields=['readiness_score', 'updated_at'])
        return user.email, job, score
