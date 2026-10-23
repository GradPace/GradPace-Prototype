import json
from collections import Counter
from pathlib import Path

from django.core.exceptions import ValidationError
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from intelligence.models import Job, JobPosting, JobSkill

DATA_DIR = Path(__file__).resolve().parents[2] / 'data'

JOB_FIELDS = ['title', 'description', 'area', 'median_annual_wage', 'employment']
POSTING_FIELDS = [
    'title',
    'company',
    'location',
    'seniority',
    'salary_min',
    'salary_max',
    'description',
]
# generated_postings.json holds only synthetic postings, so it has no source field.
DEFAULT_POSTING_SOURCE = 'generated'
# Mirrors the uniqueness the postings validator guarantees - the model has no natural key.
POSTING_KEY = ['title', 'company', 'location']


def validation_messages(error):
    if hasattr(error, 'message_dict'):
        return [f'{field}: {msg}' for field, msgs in error.message_dict.items() for msg in msgs]
    return list(error.messages)


class Command(BaseCommand):
    help = (
        'Load official_jobs.json and generated_postings.json into Job, JobSkill and '
        'JobPosting. Safe to rerun: rows are matched and updated, never duplicated. '
        'Everything is validated first, and nothing is written if anything fails.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--jobs', type=Path, default=DATA_DIR / 'official_jobs.json')
        parser.add_argument('--postings', type=Path, default=DATA_DIR / 'generated_postings.json')
        parser.add_argument(
            '--dry-run', action='store_true', help='Validate and report without writing.'
        )

    def handle(self, *args, **options):
        jobs_data = self.read_json(options['jobs'])
        postings_data = self.read_json(options['postings'])

        errors = self.validate(jobs_data, postings_data)
        if errors:
            raise CommandError(
                f'{len(errors)} validation error(s), nothing written:\n' + '\n'.join(errors)
            )

        if options['dry_run']:
            skills = sum(len(job['skills']) for job in jobs_data)
            self.stdout.write(
                f'Dry run OK: {len(jobs_data)} jobs, {skills} skills, '
                f'{len(postings_data)} postings would be seeded.'
            )
            return

        with transaction.atomic():
            counts = self.write(jobs_data, postings_data)
        for label in ['Jobs', 'Skills', 'Postings']:
            created, updated = counts[label, True], counts[label, False]
            self.stdout.write(f'{label}: {created} created, {updated} updated')

    def read_json(self, path):
        try:
            data = json.loads(Path(path).read_text())
        except (OSError, json.JSONDecodeError) as exc:
            raise CommandError(f'Could not read {path}: {exc}') from exc
        if not isinstance(data, list):
            raise CommandError(f'{path}: expected a JSON list')
        return data

    def validate(self, jobs_data, postings_data):
        """Check every row with the models' own full_clean() (objects.create() skips
        validators), plus the cross-row rules the models can't see before saving."""
        errors = []
        skill_names = {}

        for index, data in enumerate(jobs_data):
            code = data.get('soc_code')
            label = f'job #{index} {code}'
            if code in skill_names:
                errors.append(f'{label}: duplicate soc_code')
                continue
            job = Job(soc_code=code, source=data.get('source'), **self.pick(data, JOB_FIELDS))
            errors += self.clean(label, job)
            # write()'s update_or_create would raise MultipleObjectsReturned on these.
            if Job.objects.filter(soc_code=code, source=job.source).count() > 1:
                errors.append(f'{label}: more than one {job.source} Job in the database')

            names = []
            for skill in data.get('skills', []):
                skill_label = f'{label} skill {skill.get("name")!r}'
                instance = JobSkill(
                    name=skill.get('name'),
                    skill_type=skill.get('type'),
                    importance=skill.get('importance'),
                )
                errors += self.clean(skill_label, instance, exclude=['job'])
                names.append(skill.get('name'))
            duplicates = [name for name, n in Counter(names).items() if n > 1]
            if duplicates:
                errors.append(f'{label}: duplicate skill names {duplicates}')
            skill_names[code] = set(names)

        seen = set()
        for index, data in enumerate(postings_data):
            code = data.get('soc_code')
            label = f'posting #{index} {code} {data.get("title")!r}'
            posting = JobPosting(**self.posting_fields(data))
            errors += self.clean(label, posting, exclude=['job', 'skills'])
            if code not in skill_names:
                errors.append(f'{label}: soc_code not in the jobs file')
                continue
            # write() looks skills up on the posting's own job, so an unknown name is the
            # only way to fail.
            unknown = [name for name in data.get('skills', []) if name not in skill_names[code]]
            if unknown:
                errors.append(f'{label}: skills not on {code}: {unknown}')
            key = (code, *(data.get(field) for field in POSTING_KEY))
            if key in seen:
                errors.append(f'{label}: duplicate posting (same title/company/location)')
            seen.add(key)

        return errors

    def write(self, jobs_data, postings_data):
        counts = Counter()
        jobs, skills = {}, {}

        for data in jobs_data:
            job, created = Job.objects.update_or_create(
                soc_code=data['soc_code'],
                source=data['source'],
                defaults=self.pick(data, JOB_FIELDS),
            )
            counts['Jobs', created] += 1
            jobs[job.soc_code] = job
            for skill in data['skills']:
                instance, created = JobSkill.objects.update_or_create(
                    job=job,
                    name=skill['name'],
                    defaults={'skill_type': skill['type'], 'importance': skill['importance']},
                )
                counts['Skills', created] += 1
                skills[job.soc_code, instance.name] = instance

        for data in postings_data:
            job = jobs[data['soc_code']]
            fields = self.posting_fields(data)
            lookup = {field: fields.pop(field) for field in POSTING_KEY}
            posting, created = JobPosting.objects.update_or_create(
                job=job,
                **lookup,
                defaults=fields,
            )
            counts['Postings', created] += 1
            posting.set_skills([skills[job.soc_code, name] for name in data['skills']])

        return counts

    @staticmethod
    def pick(data, fields):
        return {field: data.get(field) for field in fields}

    def posting_fields(self, data):
        return {
            **self.pick(data, POSTING_FIELDS),
            'source': data.get('source', DEFAULT_POSTING_SOURCE),
        }

    @staticmethod
    def clean(label, instance, exclude=None):
        try:
            instance.full_clean(exclude=exclude, validate_unique=False)
        except ValidationError as exc:
            return [f'{label}: {message}' for message in validation_messages(exc)]
        return []
