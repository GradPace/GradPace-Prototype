"""BEST-FIT JOBS: a student's readiness for every job, ranked.

Every job has its own benchmark, so the same student can be a weak fit for
one role and a strong one for another - light on SQL for Database
Administrators, but well placed for Web Developers. This scores the student
against all of them so the dashboard can say "your strongest matches are...".

A benchmark built from only a few postings is mostly those few employers'
wish lists, so each result carries `limited_data` - the UI should show those
with a caveat (or below the others) rather than as confident matches.
"""

from intelligence.models import Job

from .job_benchmark import build_job_benchmark
from .scoring import readiness, room_to_grow, skills_of

# Benchmarks built from fewer postings than this are flagged limited_data.
# Same threshold job_benchmark uses for "enough intern/entry postings".
LIMITED_DATA_POSTINGS = 10

# How many of each job's biggest gaps to include.
TOP_GAPS = 3


def best_fit_jobs(student_profile, jobs=None):
    """[{role, overall_readiness_score, postings_used, limited_data,
    top_unmet_skills}], best match first.

    Jobs with enough data are ranked above limited_data ones, then by score,
    so a 3-posting benchmark can't crowd out well-supported matches."""
    if jobs is None:
        jobs = Job.objects.filter(area='National')

    student_skills = skills_of(student_profile)
    results = []
    for job in jobs:
        benchmark = build_job_benchmark(job)
        result = readiness(student_skills, benchmark.skills)

        unmet = [s for skills in result['skills'].values() for s in skills if not s['met']]
        unmet.sort(key=lambda s: (-room_to_grow(s), s['name']))

        results.append(
            {
                'role': {'soc_code': job.soc_code, 'title': job.title},
                'overall_readiness_score': result['overall_readiness_score'],
                'postings_used': benchmark.postings_used,
                'limited_data': benchmark.postings_used < LIMITED_DATA_POSTINGS,
                'top_unmet_skills': unmet[:TOP_GAPS],
            }
        )

    results.sort(
        key=lambda r: (r['limited_data'], -r['overall_readiness_score'], r['role']['title'])
    )
    return results
