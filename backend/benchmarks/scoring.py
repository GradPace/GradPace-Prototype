"""The READINESS SCORE (GP-66): how a student's skills measure up against
the benchmark for a job.

    student's Skill rows ─┐
                          ├─> score_against_benchmark() ─> per-dimension 0-100 scores
    job benchmark ────────┘   (job_benchmark.py)           + dimension weights
                                                                    │
                       algorithms.calculate_benchmark_score() (GP-40)┘
                                                                    │
                                  overall score + gaps + "where to focus"

Each benchmark skill the student has earns its weight, scaled by their
proficiency (1-4, see proficiency_credit). So an in-demand skill counts for
more than a rare one, and an expert earns more than a beginner. Benchmark
skills the student doesn't have earn nothing.

Dimensions are O*NET's own skill types (software / transferable /
essential), and each dimension's weight is its share of the benchmark's
total weight - so the weights come from the market data rather than being
hardcoded, and always sum to 1.

Rule-based on purpose: the SRS (Table 1) scopes the prototype to "basic
scoring" and "rule based instead of AI-driven" gap detection.
"""

from collections import Counter

from .algorithms import calculate_benchmark_score
from .catalog import label_for
from .job_benchmark import build_job_benchmark

# accounts.models.Skill stores proficiency as text. Readiness treats it as
# 1-4, and a student earns level / MAX_LEVEL of a skill's weight:
# beginner 25%, intermediate 50%, advanced 75%, expert 100%.
PROFICIENCY_LEVELS = {'beginner': 1, 'intermediate': 2, 'advanced': 3, 'expert': 4}
MAX_LEVEL = 4
# A skill listed without a rating: they have it, but haven't said how well.
UNRATED_LEVEL = 1


def proficiency_level(text):
    """Skill.proficiency_level ('beginner'...'expert', or '' if unrated) -> 1-4."""
    return PROFICIENCY_LEVELS.get(text, UNRATED_LEVEL)


def proficiency_credit(level):
    """Share of a skill's weight earned at this proficiency (1-4)."""
    return level / MAX_LEVEL


def _key(name):
    return name.strip().casefold()


def student_levels(student_skills):
    """{skill name: proficiency text} -> {normalized name: level 1-4}.

    Names are matched exactly (ignoring case and surrounding spaces) against
    a benchmark skill's O*NET name or its display label - so a picker that
    saves 'Structured query language SQL' and a student who typed 'SQL' both
    match. No partial matching: 'Microsoft' doesn't earn credit for every
    Microsoft product. If two entries normalize to the same name, the
    higher level wins."""
    levels = {}
    for name, text in student_skills.items():
        key = _key(name)
        levels[key] = max(levels.get(key, 0), proficiency_level(text))
    return levels


def level_for(levels, benchmark_skill_name):
    """The student's level (1-4) for a benchmark skill, or None if they
    don't have it. levels: from student_levels()."""
    found = [
        levels[key]
        for key in {_key(benchmark_skill_name), _key(label_for(benchmark_skill_name))}
        if key in levels
    ]
    return max(found, default=None)


def score_against_benchmark(student_skills, benchmark_skills):
    """Pure scoring step - no database access.

    student_skills: {'Python': 'advanced', 'SQL': 'beginner', ...}
                    (Skill name -> Skill.proficiency_level text)
    benchmark_skills: [BenchmarkSkill, ...] (see job_benchmark.py)

    Returns (profile, weights, skill_details):
        profile        {dimension: 0-100 score}  -> calculate_benchmark_score
        weights        {dimension: share of the benchmark's total weight} (sums to 1)
        skill_details  {dimension: [one dict per skill, most in-demand first]}
    """
    levels = student_levels(student_skills)
    earned = Counter()
    possible = Counter()
    details = {}

    for skill in sorted(benchmark_skills, key=lambda s: (-s.weight, s.name)):
        level = level_for(levels, skill.name)
        credit = proficiency_credit(level) if level is not None else 0.0
        earned[skill.skill_type] += skill.weight * credit
        possible[skill.skill_type] += skill.weight
        details.setdefault(skill.skill_type, []).append(
            {
                'name': skill.name,
                'label': label_for(skill.name),
                'demand': round(skill.weight, 3),
                'your_level': level,  # 1-4, or None = not on the student's profile
                'met': credit == 1.0,
            }
        )

    total = sum(possible.values())
    profile = {dim: round(100.0 * earned[dim] / possible[dim], 2) for dim in possible}
    weights = {dim: possible[dim] / total for dim in possible} if total else {}
    return profile, weights, details


def room_to_grow(skill_detail):
    """How much of a skill's weight the student hasn't earned yet: its
    demand x the credit still missing. A missing skill has all of it."""
    level = skill_detail['your_level']
    earned = proficiency_credit(level) if level is not None else 0.0
    return skill_detail['demand'] * (1.0 - earned)


def readiness(student_skills, benchmark_skills):
    """Score plain data end to end. Returns calculate_benchmark_score's shape
    (overall_readiness_score, gap_breakdown) plus:

        skills        per dimension, every benchmark skill with the student's
                      level, most in-demand first
        flagged_gaps  dimensions with a gap, ranked by how many overall points
                      closing them would add (gap x weight), each with its top
                      5 unmet skills ranked by room_to_grow - so a skill the
                      student lacks entirely can outrank one they already
                      have at level 3. This is the "where to focus" order.
    """
    profile, weights, details = score_against_benchmark(student_skills, benchmark_skills)
    result = calculate_benchmark_score(profile, weights)

    flagged = []
    for dimension, info in result['gap_breakdown'].items():
        if info['gap'] > 0:
            unmet = [s for s in details[dimension] if not s['met']]
            unmet.sort(key=lambda s: (-room_to_grow(s), s['name']))
            flagged.append(
                {
                    'dimension': dimension,
                    'gap': info['gap'],
                    'points_available': round(info['gap'] * info['weight'], 2),
                    'top_unmet_skills': unmet[:5],
                }
            )
    flagged.sort(key=lambda g: g['points_available'], reverse=True)

    result['skills'] = details
    result['flagged_gaps'] = flagged
    return result


def skills_of(student_profile):
    """A StudentProfile's skills as {name: proficiency text}, for readiness()."""
    return {s.name: s.proficiency_level for s in student_profile.skills.all()}


def score_student(student_profile, job, benchmark=None):
    """Score a StudentProfile's skills against a Job's benchmark. Returns
    readiness()'s result plus `benchmark`: how many postings it was built
    from, so the UI can say "based on N postings"."""
    benchmark = benchmark or build_job_benchmark(job)
    result = readiness(skills_of(student_profile), benchmark.skills)
    result['benchmark'] = {
        'postings_used': benchmark.postings_used,
        'seniorities_used': benchmark.seniorities_used,
    }
    return result
