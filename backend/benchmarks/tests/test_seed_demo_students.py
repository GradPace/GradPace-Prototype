import pytest
from django.core.management import CommandError, call_command

from accounts.models import StudentProfile
from benchmarks.best_fit import best_fit_jobs
from benchmarks.management.commands.seed_demo_students import DEMO_STUDENTS

PASSWORD = 'Zq7!fWbn2'


def run(**options):
    call_command('seed_demo_students', password=PASSWORD, **options)


def profile(email):
    return StudentProfile.objects.get(user__email=email)


def test_refuses_with_debug_off(settings, real_catalog):
    settings.DEBUG = False
    with pytest.raises(CommandError, match='production'):
        run()


def test_needs_job_data(settings, db):
    # The autouse fixture leaves no jobs, as if migrations hadn't seeded them.
    settings.DEBUG = True
    with pytest.raises(CommandError, match='migrate'):
        run()


def test_creates_students_with_skills_target_job_and_score(settings, real_catalog):
    settings.DEBUG = True
    run()

    assert StudentProfile.objects.count() == len(DEMO_STUDENTS)
    for data in DEMO_STUDENTS:
        student = profile(data['email'])
        assert student.target_job.soc_code == data['target_job']
        assert student.skills.count() == len(data['skills'])
        assert student.readiness_score is not None
        assert student.user.role.role_name == 'student'
        assert student.user.check_password(PASSWORD)


def test_every_demo_skill_is_a_real_benchmark_skill(settings, real_catalog):
    """Guards against a typo in DEMO_STUDENTS silently scoring nothing."""
    from benchmarks.catalog import skill_catalog

    catalog = {s['name'] for s in skill_catalog()}
    for data in DEMO_STUDENTS:
        assert set(data['skills']) <= catalog, data['email']


def test_demo_students_show_the_intended_story(settings, real_catalog):
    settings.DEBUG = True
    run()

    alex, priya, marcus, jordan = (profile(d['email']) for d in DEMO_STUDENTS)
    # Clearly different readiness for the same target job...
    assert alex.readiness_score > priya.readiness_score > marcus.readiness_score
    # ...and Jordan, aiming for Software Developers, fits Data Scientists best.
    assert best_fit_jobs(jordan)[0]['role']['title'] == 'Data Scientists'


def test_rerunning_resets_instead_of_duplicating(settings, real_catalog):
    settings.DEBUG = True
    run()
    first = profile(DEMO_STUDENTS[0]['email'])
    first.skills.all().delete()

    run()

    assert StudentProfile.objects.count() == len(DEMO_STUDENTS)
    assert first.skills.count() == len(DEMO_STUDENTS[0]['skills'])
