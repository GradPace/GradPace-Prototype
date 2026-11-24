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

Two optional refinements, both off by default:

- `location`: only use postings in that location (an exact match on
  JobPosting.location, e.g. 'Norfolk, VA').
- `skill_groups`: tools that do the same job (React or Angular, AWS or
  Azure) are grouped, because employers want one of them, not all. A group's
  weight is the share of postings listing ANY of its tools. See SkillGroup.
"""

from collections import Counter
from dataclasses import dataclass, field

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
class SkillGroup:
    key: str  # e.g. 'cloud'
    name: str  # e.g. 'Cloud'
    tools: tuple[str, ...]  # exact O*NET names
    weight: float  # share of the postings listing any of its tools, 0-1


@dataclass(frozen=True)
class JobBenchmark:
    job: Job
    skills: list[BenchmarkSkill]  # most in-demand first
    postings_used: int
    seniorities_used: str  # 'intern/entry' or 'all'
    groups: list[SkillGroup] = field(default_factory=list)  # only if skill_groups was given


def get_job(soc_code):
    """The national Job for an SOC code (e.g. '15-1252'), or None."""
    jobs = Job.objects.filter(soc_code=soc_code)
    return jobs.filter(area='National').first() or jobs.first()


def build_group_weights(skill_groups, posting_skill_names):
    """[SkillGroup, ...] for skill_groups ([(key, name, tools), ...]).

    posting_skill_names: one set of skill names per posting. A group's weight
    is the share of postings listing any of its tools. Unlike individual
    skills there's no MIN_DEMAND cutoff - the groups are chosen by hand. With
    no postings, every group weighs 1.0 (equal)."""
    total = len(posting_skill_names)
    groups = []
    for key, name, tools in skill_groups:
        if total:
            listed = sum(1 for names in posting_skill_names if names & set(tools))
            weight = round(listed / total, 4)
        else:
            weight = 1.0
        groups.append(SkillGroup(key, name, tuple(tools), weight))
    return groups


def build_job_benchmark(job, location=None, skill_groups=()):
    """Build the benchmark for one Job. See the module docstring.

    location: only use postings in this location, if given.
    skill_groups: [(key, name, tools), ...] to also weigh as groups - the
    result's `groups`. Empty (the default) leaves `groups` empty."""
    postings = JobPosting.objects.filter(job=job)
    if location is not None:
        postings = postings.filter(location=location)
    student_level = postings.filter(seniority__in=STUDENT_SENIORITIES)
    if student_level.count() >= MIN_STUDENT_POSTINGS:
        postings, seniorities = student_level, 'intern/entry'
    else:
        seniorities = 'all'

    total = postings.count()
    if total == 0:
        # No postings at all: fall back to the job's O*NET skill list, equally weighted.
        skills = [BenchmarkSkill(s.name, s.skill_type, 1.0) for s in job.skills.order_by('name')]
        groups = build_group_weights(skill_groups, [])
        return JobBenchmark(job, skills, postings_used=0, seniorities_used='none', groups=groups)

    counts = Counter()
    posting_skill_names = []
    for posting in postings.prefetch_related('skills'):
        posting_skills = list(posting.skills.all())
        counts.update(posting_skills)
        posting_skill_names.append({skill.name for skill in posting_skills})

    skills = [
        BenchmarkSkill(skill.name, skill.skill_type, round(count / total, 4))
        for skill, count in counts.items()
        if count / total >= MIN_DEMAND
    ]
    skills.sort(key=lambda s: (-s.weight, s.name))
    groups = build_group_weights(skill_groups, posting_skill_names)
    return JobBenchmark(
        job, skills, postings_used=total, seniorities_used=seniorities, groups=groups
    )
