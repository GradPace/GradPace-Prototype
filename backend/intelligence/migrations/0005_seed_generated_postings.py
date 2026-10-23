import json
from pathlib import Path

from django.db import migrations

POSTINGS_FILE = Path(__file__).resolve().parents[1] / 'data' / 'generated_postings.json'

POSTING_FIELDS = [
    'title',
    'company',
    'location',
    'seniority',
    'salary_min',
    'salary_max',
    'description',
]
# Mirrors the uniqueness the postings validator guarantees - the model has no natural key.
POSTING_KEY = ['title', 'company', 'location']


def seed_generated_postings(apps, schema_editor):
    """Load generated_postings.json into JobPosting. The official jobs and skills come
    from 0004; a posting whose job or skills are missing anyway is skipped rather than
    failing the whole migration."""
    Job = apps.get_model('intelligence', 'Job')
    JobPosting = apps.get_model('intelligence', 'JobPosting')

    postings = json.loads(POSTINGS_FILE.read_text())
    skipped = 0

    for data in postings:
        job = Job.objects.filter(soc_code=data['soc_code'], source='official').first()
        if job is None:
            skipped += 1
            continue
        skills = list(job.skills.filter(name__in=data['skills']))
        if len(skills) != len(set(data['skills'])):
            skipped += 1
            continue

        fields = {field: data.get(field) for field in POSTING_FIELDS}
        lookup = {field: fields.pop(field) for field in POSTING_KEY}
        posting, _ = JobPosting.objects.update_or_create(
            job=job,
            **lookup,
            defaults={**fields, 'source': data.get('source', 'generated')},
        )
        posting.skills.set(skills)

    if skipped:
        print(f'\n  Skipped {skipped} generated posting(s) with no matching job/skills.')


def remove_generated_postings(apps, schema_editor):
    JobPosting = apps.get_model('intelligence', 'JobPosting')
    JobPosting.objects.filter(source='generated').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('intelligence', '0004_seed_official_jobs'),
    ]

    operations = [
        migrations.RunPython(seed_generated_postings, remove_generated_postings),
    ]
