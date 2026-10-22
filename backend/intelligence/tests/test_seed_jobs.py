import copy
import json
from io import StringIO

import pytest
from django.core.management import CommandError, call_command

from ..management.commands.seed_jobs import DATA_DIR
from ..models import Job, JobPosting, JobSkill

JOBS = [
    {
        'title': 'Software Developers',
        'soc_code': '15-1252',
        'description': 'Research, design, and develop computer software.',
        'area': 'National',
        'median_annual_wage': 135980,
        'employment': 1687890,
        'source': 'official',
        'skills': [
            {'name': 'Programming', 'importance': 4.0, 'type': 'transferable'},
            {'name': 'Critical Thinking', 'importance': 3.88, 'type': 'essential'},
            {'name': 'Python', 'importance': None, 'type': 'software'},
        ],
    },
    {
        'title': 'Data Scientists',
        'soc_code': '15-2051',
        'description': 'Develop and implement methods to analyze data.',
        'area': 'National',
        'median_annual_wage': 120230,
        'employment': 262440,
        'source': 'official',
        'skills': [{'name': 'R', 'importance': None, 'type': 'software'}],
    },
]
POSTINGS = [
    {
        'soc_code': '15-1252',
        'title': 'Junior Software Developer',
        'company': 'Quillfeather Labs',
        'location': 'Norfolk, VA',
        'seniority': 'entry',
        'salary_min': 90000,
        'salary_max': 100000,
        'description': 'Build things. Ship them.',
        'skills': ['Python', 'Programming'],
    },
]


def write_files(tmp_path, jobs=None, postings=None):
    jobs_path, postings_path = tmp_path / 'jobs.json', tmp_path / 'postings.json'
    jobs_path.write_text(json.dumps(JOBS if jobs is None else jobs))
    postings_path.write_text(json.dumps(POSTINGS if postings is None else postings))
    return jobs_path, postings_path


def seed(jobs_path, postings_path, **options):
    out = StringIO()
    call_command('seed_jobs', jobs=jobs_path, postings=postings_path, stdout=out, **options)
    return out.getvalue()


def table_counts():
    return Job.objects.count(), JobSkill.objects.count(), JobPosting.objects.count()


@pytest.mark.django_db
def test_seeds_real_data_files():
    seed(DATA_DIR / 'official_jobs.json', DATA_DIR / 'generated_postings.json')

    jobs = json.loads((DATA_DIR / 'official_jobs.json').read_text())
    postings = json.loads((DATA_DIR / 'generated_postings.json').read_text())
    assert table_counts() == (
        len(jobs),
        sum(len(job['skills']) for job in jobs),
        len(postings),
    )
    for posting in JobPosting.objects.prefetch_related('skills'):
        assert all(skill.job_id == posting.job_id for skill in posting.skills.all())


@pytest.mark.django_db
def test_running_twice_gives_same_counts(tmp_path):
    paths = write_files(tmp_path)

    first = seed(*paths)
    counts = table_counts()
    links = JobPosting.skills.through.objects.count()
    second = seed(*paths)

    assert counts == (2, 4, 1)
    assert table_counts() == counts
    assert JobPosting.skills.through.objects.count() == links == 2
    assert 'Jobs: 2 created, 0 updated' in first
    assert 'Jobs: 0 created, 2 updated' in second
    assert 'Skills: 0 created, 4 updated' in second
    assert 'Postings: 0 created, 1 updated' in second


@pytest.mark.django_db
def test_rerun_updates_fields_in_place(tmp_path):
    seed(*write_files(tmp_path))
    jobs = copy.deepcopy(JOBS)
    jobs[0]['median_annual_wage'] = 140000
    jobs[0]['skills'][0]['importance'] = 4.5

    seed(*write_files(tmp_path, jobs=jobs))

    job = Job.objects.get(soc_code='15-1252')
    assert job.median_annual_wage == 140000
    assert job.skills.get(name='Programming').importance == 4.5
    assert table_counts() == (2, 4, 1)


def break_importance(jobs, postings):
    jobs[0]['skills'][0]['importance'] = 6


def break_skill_type(jobs, postings):
    jobs[0]['skills'][0]['type'] = 'knowledge'


def break_posting_skill(jobs, postings):
    postings[0]['skills'].append('R')  # belongs to 15-2051, not 15-1252


def break_salary(jobs, postings):
    postings[0]['salary_min'], postings[0]['salary_max'] = 100000, 90000


def break_soc_code(jobs, postings):
    postings[0]['soc_code'] = '99-9999'


@pytest.mark.django_db
@pytest.mark.parametrize(
    'break_data',
    [break_importance, break_skill_type, break_posting_skill, break_salary, break_soc_code],
)
def test_bad_data_writes_nothing(tmp_path, break_data):
    jobs, postings = copy.deepcopy(JOBS), copy.deepcopy(POSTINGS)
    break_data(jobs, postings)

    with pytest.raises(CommandError, match='nothing written'):
        seed(*write_files(tmp_path, jobs=jobs, postings=postings))

    assert table_counts() == (0, 0, 0)


@pytest.mark.django_db
def test_bad_data_leaves_existing_rows_untouched(tmp_path):
    seed(*write_files(tmp_path))
    jobs, postings = copy.deepcopy(JOBS), copy.deepcopy(POSTINGS)
    jobs[0]['title'] = 'Renamed Developers'
    break_salary(jobs, postings)

    with pytest.raises(CommandError):
        seed(*write_files(tmp_path, jobs=jobs, postings=postings))

    assert Job.objects.get(soc_code='15-1252').title == 'Software Developers'
    assert table_counts() == (2, 4, 1)


@pytest.mark.django_db
def test_dry_run_writes_nothing(tmp_path):
    out = seed(*write_files(tmp_path), dry_run=True)

    assert 'Dry run OK: 2 jobs, 4 skills, 1 postings' in out
    assert table_counts() == (0, 0, 0)
