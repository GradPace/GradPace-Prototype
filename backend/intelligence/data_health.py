"""Admin data-health report (GP-62): how complete the seeded job catalog is,
and how many saved student locations places.lookup can place (the event
distance needs one). Counts come straight from the database, not from
data/validate_postings.py, which checks the JSON files before seeding.
"""

from collections import Counter

from django.db.models import Count, Max, Q

from accounts.models import StudentProfile

from . import places
from .models import Job, JobPosting, JobSkill

# Below this many postings an occupation is flagged - the same floor
# data/validate_postings.py (MIN_PER_OCCUPATION) holds the generated data to.
MIN_POSTINGS = 3
MAX_UNRECOGNIZED = 20


def _by_source(model):
    """{'total': n, <source>: n, ...} - one key per SOURCE_CHOICES value, so
    a source with no rows still shows as 0."""
    counts = {'total': Count('id')}
    for source, _ in model.SOURCE_CHOICES:
        counts[source] = Count('id', filter=Q(source=source))
    return model.objects.aggregate(**counts)


def catalog_totals():
    return {
        'jobs': _by_source(Job),
        # JobSkill has no source field.
        'skills': {'total': JobSkill.objects.count()},
        'postings': _by_source(JobPosting),
    }


def catalog_updated_at():
    """When the catalog was last seeded (or edited), or None if it's empty.
    There's no seeding timestamp of its own, but seed_jobs saves every row
    through update_or_create, which moves each one's updated_at."""
    latest = [
        model.objects.aggregate(latest=Max('updated_at'))['latest']
        for model in (Job, JobSkill, JobPosting)
    ]
    return max((when for when in latest if when is not None), default=None)


def occupations():
    """One row per Job (a soc_code can be both official and generated), with
    flags for the gaps that weaken scoring."""
    jobs = (
        Job.objects.annotate(
            posting_count=Count('postings', distinct=True),
            skill_count=Count('skills', distinct=True),
        )
        .order_by('soc_code', 'source')
        .values('soc_code', 'title', 'source', 'posting_count', 'skill_count', 'median_annual_wage')
    )
    return [
        {
            **job,
            'few_postings': job['posting_count'] < MIN_POSTINGS,
            'missing_wage': job['median_annual_wage'] is None,
            'no_skills': job['skill_count'] == 0,
        }
        for job in jobs
    ]


def student_locations():
    """Counts only - no names, emails or ids. location is encrypted at rest,
    so it can't be grouped in SQL: every value is decrypted and counted here."""
    values = list(StudentProfile.objects.values_list('location', flat=True))
    given = Counter(value.strip() for value in values if value and value.strip())
    unrecognized = Counter(
        {value: count for value, count in given.items() if places.lookup(value) is None}
    )
    most_common = sorted(unrecognized.items(), key=lambda item: (-item[1], item[0]))
    return {
        'profiles': len(values),
        'with_location': given.total(),
        'recognized': given.total() - unrecognized.total(),
        'unrecognized': unrecognized.total(),
        'unrecognized_values': [
            {'location': value, 'count': count} for value, count in most_common[:MAX_UNRECOGNIZED]
        ],
    }


def report():
    return {
        'totals': catalog_totals(),
        'catalog_updated_at': catalog_updated_at(),
        'occupations': occupations(),
        'student_locations': student_locations(),
    }
