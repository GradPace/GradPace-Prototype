"""The BENCHMARK: what the market wants for each job.

For a Job (from the intelligence app, GP-41), this builds a list of skills
with a weight each - "Software Developers need Programming (in 96% of
postings), Git (78%), Python (39%)...". A student's readiness score is
measured against this list (see scoring.py).

How a job's benchmark is built:

1. Pick the postings that represent the job. Students compete for intern and
   entry-level roles, so those are used when there are at least
   MIN_STUDENT_POSTINGS of them. Most jobs in the seed data have far fewer
   (several have just 1), and a benchmark built from one posting is just that
   posting's wish list - so below the threshold, all of the job's postings
   are used instead.
2. A skill's weight is the share of those postings that list it.
3. Skills below MIN_DEMAND are left out. They're rare enough that
   requiring them would mostly just drag every student's score down.

The weights are shares (0-1), but scoring only cares about their relative
size, so any positive numbers work - a hand-tuned benchmark could plug in
here later without changing scoring.py.
"""

from collections import Counter
from dataclasses import dataclass

from intelligence.models import Job, JobPosting

STUDENT_SENIORITIES = ('intern', 'entry')

# Below this many intern/entry postings, use all of the job's postings.
MIN_STUDENT_POSTINGS = 10

# Skills listed in fewer than this share of postings aren't benchmarked.
MIN_DEMAND = 0.10


@dataclass(frozen=True)
class BenchmarkSkill:
    name: str  # exact O*NET name, e.g. 'Structured query language SQL'
    skill_type: str  # 'software' / 'transferable' / 'essential'
    weight: float  # share of the postings that list it, 0-1


@dataclass(frozen=True)
class JobBenchmark:
    job: Job
    skills: list[BenchmarkSkill]  # most in-demand first
    postings_used: int
    seniorities_used: str  # 'intern/entry' or 'all'


def get_job(soc_code):
    """The national Job for an SOC code (e.g. '15-1252'), or None."""
    jobs = Job.objects.filter(soc_code=soc_code)
    return jobs.filter(area='National').first() or jobs.first()


def build_job_benchmark(job):
    """Build the benchmark for one Job. See the module docstring."""
    postings = JobPosting.objects.filter(job=job)
    student_level = postings.filter(seniority__in=STUDENT_SENIORITIES)
    if student_level.count() >= MIN_STUDENT_POSTINGS:
        postings, seniorities = student_level, 'intern/entry'
    else:
        seniorities = 'all'

    total = postings.count()
    if total == 0:
        # No postings at all: fall back to the job's O*NET skill list, equally weighted.
        skills = [BenchmarkSkill(s.name, s.skill_type, 1.0) for s in job.skills.order_by('name')]
        return JobBenchmark(job, skills, postings_used=0, seniorities_used='none')

    counts = Counter()
    for posting in postings.prefetch_related('skills'):
        counts.update(posting.skills.all())

    skills = [
        BenchmarkSkill(skill.name, skill.skill_type, round(count / total, 4))
        for skill, count in counts.items()
        if count / total >= MIN_DEMAND
    ]
    skills.sort(key=lambda s: (-s.weight, s.name))
    return JobBenchmark(job, skills, postings_used=total, seniorities_used=seniorities)
