"""SCORING CONFIGS: extra inputs for the readiness score of a particular
kind of student.

The base score (scoring.py) is skills only, against every posting for a job.
A ScoringConfig refines that for one school + location + role, e.g. Old
Dominion students going for Software Developer jobs in Norfolk:

- skill_groups: tools that do the same job are grouped (see job_benchmark.py)
- courses: the school's courses that prepare a student for the role
- certificates: ones that earn a bonus
- level_credits: how much of a group's points each proficiency level earns

Students with no matching config are scored exactly as before.
"""

from dataclasses import dataclass, field

# Tool names are the exact O*NET names the skill picker saves.
ODU_SKILL_GROUPS = (
    ('fundamentals', 'Programming fundamentals', ('Programming',)),
    (
        'language',
        'Main language',
        ('Python', 'Oracle Java', 'C#', 'C++', 'JavaScript', 'TypeScript'),
    ),
    ('version_control', 'Version control', ('Git', 'GitHub')),
    ('databases', 'Databases', ('Structured query language SQL', 'PostgreSQL', 'NoSQL')),
    ('backend', 'Backend / APIs', ('RESTful API', 'Node.js', 'Spring Boot')),
    ('frontend', 'Frontend framework', ('React', 'Google Angular')),
    ('cloud', 'Cloud', ('Amazon Web Services AWS software', 'Microsoft Azure software')),
    ('devops', 'DevOps', ('Docker', 'Jenkins CI')),
    ('os', 'Operating systems', ('Linux',)),
    ('problem_solving', 'Problem solving', ('Critical Thinking',)),
)

# ODU CS courses that prepare a student for Software Developer roles.
ODU_COURSES = (
    ('CS 151', 'Introduction to Programming with Java'),
    ('CS 170', 'Introduction to Computer Architecture I'),
    ('CS 251', 'Programming with Java'),
    ('CS 252', 'Introduction to Unix for Programmers'),
    ('CS 330', 'Object-Oriented Programming and Design'),
    ('CS 350', 'Introduction to Software Engineering'),
    ('CS 361', 'Data Structures and Algorithms'),
    ('CS 381', 'Introduction to Discrete Structures'),
    ('CS 410', 'Professional Workforce Development I'),
    ('CS 411W', 'Professional Workforce Development II'),
    ('CS 450', 'Database Concepts'),
    ('CS 471', 'Operating Systems'),
)

ODU_CERTIFICATES = (
    'AWS Certified Cloud Practitioner',
    'CompTIA Network+',
    'Microsoft Certified: Azure Fundamentals',
    'CompTIA Security+',
    'Oracle Certified Associate, Java SE Programmer',
)


@dataclass(frozen=True)
class ScoringConfig:
    soc_code: str  # the role, e.g. '15-1252'
    school: str  # matched against StudentProfile.uni
    location: str  # matched against StudentProfile.location; also filters postings
    skill_groups: tuple  # ((key, name, (tool, ...)), ...)
    courses: tuple  # ((code, name), ...) - equal points each
    certificates: tuple  # names that earn the bonus

    # Points. skills_points + courses_points should equal max_score; the
    # certificate bonus goes on top, and the total is capped at max_score.
    skills_points: int = 50
    courses_points: int = 50
    cert_bonus_each: int = 5
    cert_bonus_max: int = 10
    max_score: int = 100
    next_steps_count: int = 3

    # Skill.proficiency_level -> (label shown in the UI, share of a group's
    # points). Stored with the existing values so no migration is needed.
    levels: dict = field(
        default_factory=lambda: {
            'beginner': ('Learning', 0.25),
            'intermediate': ('Practicing', 0.60),
            'expert': ('Project ready', 1.00),
        }
    )
    # Values the UI doesn't offer: 'advanced' (older rows) counts as
    # Practicing, unrated as Learning.
    level_aliases: dict = field(
        default_factory=lambda: {'advanced': 'intermediate', '': 'beginner'}
    )

    def level_credit(self, text):
        """Skill.proficiency_level -> (label, credit). Unknown text counts as
        the lowest level."""
        lowest = next(iter(self.levels))
        return self.levels.get(self.level_aliases.get(text, text), self.levels[lowest])


ODU_SOFTWARE_DEVELOPER = ScoringConfig(
    soc_code='15-1252',  # Software Developers
    school='Old Dominion University',
    location='Norfolk, VA',
    skill_groups=ODU_SKILL_GROUPS,
    courses=ODU_COURSES,
    certificates=ODU_CERTIFICATES,
)

CONFIGS = [ODU_SOFTWARE_DEVELOPER]


def _same(a, b):
    return (a or '').strip().casefold() == (b or '').strip().casefold()


def find_config(soc_code, school, location):
    """The ScoringConfig for this role, school and location, or None. School
    and location ignore case and surrounding spaces."""
    for config in CONFIGS:
        if (
            soc_code == config.soc_code
            and _same(school, config.school)
            and _same(location, config.location)
        ):
            return config
    return None


def get_config(student_profile, job):
    """The ScoringConfig for this student scored against this job, or None
    (use the base score). Needs the job, the student's school and their
    location to all match."""
    return find_config(job.soc_code, student_profile.uni, student_profile.location)
