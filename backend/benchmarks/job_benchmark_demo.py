"""Demo version of job_benchmark.py, scoped to one school, role and location.
Instead of weighting each tool on its own, tools that do the same job are
grouped (React or Angular, AWS or Azure) - employers want one of them, not
all of them.

How the benchmark is built:

1. Postings: the role's postings in LOCATION - intern/entry only when there
   are at least MIN_STUDENT_POSTINGS of them (same rule as job_benchmark.py),
   otherwise all of them.
2. A group's weight is the share of those postings listing ANY of its tools.

scoring_demo.py turns the weights into points.
"""

from dataclasses import dataclass

from intelligence.models import Job, JobPosting

from .job_benchmark import MIN_STUDENT_POSTINGS, STUDENT_SENIORITIES, get_job

ROLE_SOC_CODE = '15-1252'  # Software Developers
SCHOOL = 'Old Dominion University'
LOCATION = 'Norfolk, VA'

# Tool names are the exact O*NET names the skill picker saves.
SKILL_GROUPS = [
    ('fundamentals', 'Programming fundamentals', ['Programming']),
    (
        'language',
        'Main language',
        ['Python', 'Oracle Java', 'C#', 'C++', 'JavaScript', 'TypeScript'],
    ),
    ('version_control', 'Version control', ['Git', 'GitHub']),
    ('databases', 'Databases', ['Structured query language SQL', 'PostgreSQL', 'NoSQL']),
    ('backend', 'Backend / APIs', ['RESTful API', 'Node.js', 'Spring Boot']),
    ('frontend', 'Frontend framework', ['React', 'Google Angular']),
    ('cloud', 'Cloud', ['Amazon Web Services AWS software', 'Microsoft Azure software']),
    ('devops', 'DevOps', ['Docker', 'Jenkins CI']),
    ('os', 'Operating systems', ['Linux']),
    ('problem_solving', 'Problem solving', ['Critical Thinking']),
]


@dataclass(frozen=True)
class SkillGroup:
    key: str  # e.g. 'cloud'
    name: str  # e.g. 'Cloud'
    tools: tuple[str, ...]
    weight: float  # share of the postings listing any of its tools, 0-1


@dataclass(frozen=True)
class JobBenchmarkDemo:
    job: Job
    groups: list[SkillGroup]  # in SKILL_GROUPS order
    postings_used: int
    seniorities_used: str  # 'intern/entry' or 'all'


def get_demo_job():
    """The demo role's Job, or None if the job data isn't seeded."""
    return get_job(ROLE_SOC_CODE)


def build_job_benchmark_demo(job):
    """Build the demo benchmark for a Job. See the module docstring."""
    postings = JobPosting.objects.filter(job=job, location=LOCATION)
    student_level = postings.filter(seniority__in=STUDENT_SENIORITIES)
    if student_level.count() >= MIN_STUDENT_POSTINGS:
        postings, seniorities = student_level, 'intern/entry'
    else:
        seniorities = 'all'

    posting_skills = [
        {skill.name for skill in posting.skills.all()}
        for posting in postings.prefetch_related('skills')
    ]
    total = len(posting_skills)

    groups = []
    for key, name, tools in SKILL_GROUPS:
        if total:
            listed = sum(1 for names in posting_skills if names & set(tools))
            weight = round(listed / total, 4)
        else:
            # No postings in LOCATION: weight every group equally.
            weight = 1.0
        groups.append(SkillGroup(key, name, tuple(tools), weight))
    return JobBenchmarkDemo(job, groups, postings_used=total, seniorities_used=seniorities)
