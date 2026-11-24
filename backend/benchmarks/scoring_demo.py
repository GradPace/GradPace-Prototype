"""The DEMO READINESS SCORE (GP-82): how ready an ODU student is for a
Software Developer role in Norfolk.

Demo version of scoring.py:

    skills    out of SKILLS_POINTS   best tool per skill group, by level
  + courses   out of COURSES_POINTS  ODU courses taken, equal points each
  + bonus     CERT_BONUS_EACH per relevant certificate, up to CERT_BONUS_MAX
  = readiness, capped at MAX_SCORE

Skills and courses are the two dimensions of Carly's GP-40 formula
(algorithms.calculate_benchmark_score); the certificate bonus is added on
top. A skill group's points are its share of the benchmark's total weight
(job_benchmark_demo.py), so groups more postings ask for are worth more.
"""

import re

from .algorithms import calculate_benchmark_score
from .catalog import label_for
from .job_benchmark_demo import LOCATION, SCHOOL
from .scoring import skills_of

SKILLS_POINTS = 50
COURSES_POINTS = 50
CERT_BONUS_EACH = 5
CERT_BONUS_MAX = 10
MAX_SCORE = 100

# Skill.proficiency_level -> (label shown in the UI, share of a group's
# points). Stored with the existing values so no migration is needed.
LEVELS = {
    'beginner': ('Learning', 0.25),
    'intermediate': ('Practicing', 0.60),
    'expert': ('Project ready', 1.00),
}
# Values the demo UI doesn't offer: 'advanced' (older rows) counts as
# Practicing, unrated as Learning.
LEVEL_ALIASES = {'advanced': 'intermediate', '': 'beginner'}

# ODU CS courses that prepare a student for Software Developer roles, each
# worth an equal share of COURSES_POINTS. Matched on course code, ignoring
# case and spaces ('cs361' == 'CS 361').
COURSES = [
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
]

# Certificates that earn the bonus. Matched on name, ignoring case.
CERTIFICATES = [
    'AWS Certified Cloud Practitioner',
    'CompTIA Network+',
    'Microsoft Certified: Azure Fundamentals',
    'CompTIA Security+',
    'Oracle Certified Associate, Java SE Programmer',
]

# How many "what to work on next" items to return.
NEXT_STEPS_COUNT = 3


def level_of(text):
    """Skill.proficiency_level -> (label, credit)."""
    return LEVELS.get(LEVEL_ALIASES.get(text, text), LEVELS['beginner'])


def _key(text):
    return text.strip().casefold()


def _course_key(code):
    return re.sub(r'\s+', '', code).upper()


def score_skills(student_skills, groups):
    """Points earned for skills, out of SKILLS_POINTS. Pure - no database.

    student_skills: {'Python': 'expert', ...} (Skill name -> proficiency text)
    groups: [SkillGroup, ...] from job_benchmark_demo

    A group earns its points x the credit of the student's best tool in it.
    A tool matches on its O*NET name or its display label ('SQL').
    Returns (points earned, one dict per group)."""
    have = {_key(name): text for name, text in student_skills.items()}
    total_weight = sum(group.weight for group in groups)
    earned_total = 0.0
    details = []

    for group in groups:
        possible = SKILLS_POINTS * group.weight / total_weight if total_weight else 0.0
        best = None  # (credit, tool, level label)
        for tool in group.tools:
            text = have.get(_key(tool), have.get(_key(label_for(tool))))
            if text is None:
                continue
            label, credit = level_of(text)
            if best is None or credit > best[0]:
                best = (credit, tool, label)

        earned = possible * best[0] if best else 0.0
        earned_total += earned
        details.append(
            {
                'key': group.key,
                'name': group.name,
                'points': round(earned, 2),
                'out_of': round(possible, 2),
                'best_tool': label_for(best[1]) if best else None,
                'level': best[2] if best else None,  # 'Learning' / ... / None
                'options': [{'name': tool, 'label': label_for(tool)} for tool in group.tools],
            }
        )
    return earned_total, details


def score_courses(course_codes):
    """Points earned for COURSES taken, out of COURSES_POINTS.
    Returns (points earned, one dict per course)."""
    taken = {_course_key(code) for code in course_codes}
    each = COURSES_POINTS / len(COURSES)
    details = [
        {'code': code, 'name': name, 'taken': _course_key(code) in taken, 'points': round(each, 2)}
        for code, name in COURSES
    ]
    return each * sum(course['taken'] for course in details), details


def certificate_bonus(certificate_names):
    """Bonus for relevant CERTIFICATES, up to CERT_BONUS_MAX.
    Returns (bonus, names of the certificates that counted)."""
    have = {_key(name) for name in certificate_names}
    counted = [name for name in CERTIFICATES if _key(name) in have]
    return min(CERT_BONUS_MAX, CERT_BONUS_EACH * len(counted)), counted


def next_steps(skill_details, course_details):
    """The NEXT_STEPS_COUNT things that would add the most points: skill
    groups not at full credit, and courses not taken."""
    steps = [
        {
            'kind': 'skill',
            'name': group['name'],
            'points_available': round(group['out_of'] - group['points'], 2),
            'options': [option['label'] for option in group['options']],
        }
        for group in skill_details
        if group['out_of'] - group['points'] >= 0.01
    ]
    steps += [
        {
            'kind': 'course',
            'name': f'{course["code"]} {course["name"]}',
            'points_available': course['points'],
            'options': [],
        }
        for course in course_details
        if not course['taken']
    ]
    steps.sort(key=lambda step: -step['points_available'])
    return steps[:NEXT_STEPS_COUNT]


def readiness_demo(student_skills, course_codes, certificate_names, groups):
    """Score plain data end to end. Returns calculate_benchmark_score's shape
    (overall_readiness_score, gap_breakdown) plus skills, courses,
    certificates and next_steps for the dashboard."""
    skills_earned, skill_details = score_skills(student_skills, groups)
    courses_earned, course_details = score_courses(course_codes)
    bonus, counted = certificate_bonus(certificate_names)

    # GP-40 formula with two dimensions, each scored 0-100.
    result = calculate_benchmark_score(
        {
            'skills': round(100.0 * skills_earned / SKILLS_POINTS, 2),
            'courses': round(100.0 * courses_earned / COURSES_POINTS, 2),
        },
        {'skills': SKILLS_POINTS / MAX_SCORE, 'courses': COURSES_POINTS / MAX_SCORE},
    )
    result['overall_readiness_score'] = min(
        MAX_SCORE, round(result['overall_readiness_score'] + bonus, 2)
    )
    result['skills'] = {
        'points': round(skills_earned, 2),
        'out_of': SKILLS_POINTS,
        'groups': skill_details,
    }
    result['courses'] = {
        'points': round(courses_earned, 2),
        'out_of': COURSES_POINTS,
        'list': course_details,
    }
    result['certificates'] = {
        'bonus': bonus,
        'max_bonus': CERT_BONUS_MAX,
        'counted': counted,
        'options': CERTIFICATES,
    }
    result['next_steps'] = next_steps(skill_details, course_details)
    return result


def score_student_demo(student_profile, benchmark):
    """Score a StudentProfile against a JobBenchmarkDemo. Returns
    readiness_demo()'s result plus `benchmark`, so the UI can say "based on
    N postings in Norfolk"."""
    result = readiness_demo(
        skills_of(student_profile),
        [course.course_code for course in student_profile.taken_classes.all()],
        [certificate.name for certificate in student_profile.certificates.all()],
        benchmark.groups,
    )
    result['benchmark'] = {
        'school': SCHOOL,
        'location': LOCATION,
        'postings_used': benchmark.postings_used,
        'seniorities_used': benchmark.seniorities_used,
    }
    return result
