"""Create demo students for the GP-82 demo dashboard: ODU students with
skills, courses and certificates, at different readiness levels for a
Software Developer role in Norfolk.

Demo version of seed_demo_students.py:

    uv run manage.py migrate              # also loads the BLS job data
    uv run manage.py seed_demo_students_demo --password <something memorable>

Safe to rerun: each student is matched by email, and their skills, courses
and certificates are reset to the definitions below. Uses its own emails and
student IDs, so it doesn't touch seed_demo_students' accounts. Prints each
student's login and demo readiness score. Refuses to run with DEBUG off (i.e.
production) unless --allow-production is passed, since it creates accounts
with a known password.
"""

import secrets

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import Certificate, Role, Skill, StudentProfile, TakenClass
from benchmarks.job_benchmark_demo import LOCATION, SCHOOL, build_job_benchmark_demo, get_demo_job
from benchmarks.scoring_demo import CERTIFICATES, COURSES, score_student_demo

from .seed_demo_students import DEMO_MAJOR

User = get_user_model()

# Skill names are exact O*NET names, as the skill picker saves them. Levels
# are the demo's three: 'beginner' (Learning), 'intermediate' (Practicing),
# 'expert' (Project ready). Course codes and certificate names must be in
# scoring_demo's COURSES and CERTIFICATES.
DEMO_STUDENTS = [
    {
        # Senior with an internship - close to career ready.
        'email': 'odu.alex@example.com',
        'first_name': 'Alex',
        'last_name': 'Rivera',
        'student_id': 'ODUDEMO01',
        'start_year': 2023,
        'skills': {
            'Programming': 'expert',
            'Python': 'expert',
            'Oracle Java': 'intermediate',
            'Git': 'expert',
            'GitHub': 'intermediate',
            'Structured query language SQL': 'intermediate',
            'PostgreSQL': 'intermediate',
            'RESTful API': 'intermediate',
            'Node.js': 'intermediate',
            'React': 'intermediate',
            'Amazon Web Services AWS software': 'intermediate',
            'Docker': 'intermediate',
            'Linux': 'intermediate',
            'Critical Thinking': 'intermediate',
        },
        'courses': [
            'CS 151',
            'CS 170',
            'CS 251',
            'CS 252',
            'CS 330',
            'CS 350',
            'CS 361',
            'CS 381',
            'CS 410',
            'CS 471',
        ],
        'certificates': ['AWS Certified Cloud Practitioner'],
    },
    {
        # Junior - solid coursework, still building tooling.
        'email': 'odu.priya@example.com',
        'first_name': 'Priya',
        'last_name': 'Shah',
        'student_id': 'ODUDEMO02',
        'start_year': 2024,
        'skills': {
            'Programming': 'intermediate',
            'Oracle Java': 'expert',
            'Python': 'intermediate',
            'Git': 'intermediate',
            'Structured query language SQL': 'intermediate',
            'Linux': 'beginner',
            'Critical Thinking': 'intermediate',
        },
        'courses': ['CS 151', 'CS 170', 'CS 251', 'CS 252', 'CS 330', 'CS 361', 'CS 381'],
        'certificates': [],
    },
    {
        # Sophomore - just getting started.
        'email': 'odu.marcus@example.com',
        'first_name': 'Marcus',
        'last_name': 'Lee',
        'student_id': 'ODUDEMO03',
        'start_year': 2025,
        'skills': {
            'Programming': 'beginner',
            'Oracle Java': 'beginner',
            'Git': 'beginner',
        },
        'courses': ['CS 151', 'CS 170', 'CS 251'],
        'certificates': [],
    },
]


def check_demo_students():
    """Every course code and certificate name must be one scoring_demo
    counts - otherwise the student silently earns nothing for it."""
    course_codes = {code for code, _ in COURSES}
    problems = [
        f'{student["email"]}: unknown {kind} {value!r}'
        for student in DEMO_STUDENTS
        for kind, values, known in (
            ('course', student['courses'], course_codes),
            ('certificate', student['certificates'], CERTIFICATES),
        )
        for value in values
        if value not in known
    ]
    if problems:
        raise CommandError('\n'.join(problems))


class Command(BaseCommand):
    help = 'Create GP-82 demo students with skills, courses and certificates (dev/demo use only).'

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

        check_demo_students()
        job = get_demo_job()
        if job is None:
            raise CommandError('No Software Developers job data - run migrate first.')
        benchmark = build_job_benchmark_demo(job)

        password = options['password'] or secrets.token_urlsafe(12)
        student_role = Role.objects.get(role_name='student')

        with transaction.atomic():
            results = [
                self.create_student(student, job, benchmark, password, student_role)
                for student in DEMO_STUDENTS
            ]

        self.stdout.write(self.style.SUCCESS(f'{len(results)} demo students ready.'))
        for email, score in results:
            self.stdout.write(f'  {email:<26} demo readiness {score:>6.2f}')
        if not options['password']:
            self.stdout.write(f'Password for all of them: {password}')

    def create_student(self, data, job, benchmark, password, role):
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
                'uni': SCHOOL,
                'location': LOCATION,
                'target_job': job,
            },
        )

        profile.skills.all().delete()
        Skill.objects.bulk_create(
            Skill(student=profile, name=name, proficiency_level=level)
            for name, level in data['skills'].items()
        )

        # Two courses a semester, fall then spring, from start_year.
        course_names = dict(COURSES)
        profile.taken_classes.all().delete()
        TakenClass.objects.bulk_create(
            TakenClass(
                student=profile,
                course_code=code,
                course_name=course_names[code],
                semester='fall' if (i // 2) % 2 == 0 else 'spring',
                year=data['start_year'] + (i // 2 + 1) // 2,
            )
            for i, code in enumerate(data['courses'])
        )

        profile.certificates.all().delete()
        Certificate.objects.bulk_create(
            Certificate(student=profile, name=name, issuing_organization=name.split()[0])
            for name in data['certificates']
        )

        # The demo score isn't saved to readiness_score (see views_demo.py).
        return user.email, score_student_demo(profile, benchmark)['overall_readiness_score']
