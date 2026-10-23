import json
from pathlib import Path

from django.db import migrations

JOBS_FILE = Path(__file__).resolve().parents[1] / 'data' / 'official_jobs.json'

JOB_FIELDS = ['title', 'description', 'area', 'median_annual_wage', 'employment']


def seed_official_jobs(apps, schema_editor):
    """Load official_jobs.json into Job and JobSkill. Rows are matched on
    (soc_code, source) and (job, name), so rerunning seed_jobs afterwards updates
    them rather than duplicating."""
    Job = apps.get_model('intelligence', 'Job')
    JobSkill = apps.get_model('intelligence', 'JobSkill')

    for data in json.loads(JOBS_FILE.read_text()):
        job, _ = Job.objects.update_or_create(
            soc_code=data['soc_code'],
            source=data['source'],
            defaults={field: data.get(field) for field in JOB_FIELDS},
        )
        for skill in data['skills']:
            JobSkill.objects.update_or_create(
                job=job,
                name=skill['name'],
                defaults={'skill_type': skill['type'], 'importance': skill['importance']},
            )


def remove_official_jobs(apps, schema_editor):
    # Skills and postings cascade.
    Job = apps.get_model('intelligence', 'Job')
    Job.objects.filter(source='official').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('intelligence', '0003_jobposting'),
    ]

    operations = [
        migrations.RunPython(seed_official_jobs, remove_official_jobs),
    ]
