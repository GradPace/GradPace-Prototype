"""
RELEVANCE SCORING AGAINST STUDENT GAP PROFILE

Calculates how relevant learning content or tasks are to a student's skill gaps.

Gaps are derived from `scoring.py` (readiness output) or calculated directly from
unearned skill weights.
"""

from .scoring import student_levels, level_for, proficiency_credit, room_to_grow


def calculate_student_gaps(student_skills, benchmark_skills):
    """
    Extracts skill gaps for a student against a target job benchmark.

    student_skills: {'Python': 'advanced', 'SQL': 'beginner', ...}
    benchmark_skills: [BenchmarkSkill, ...]

    Returns:
        dict: {skill_name: gap_weight}
        Where gap_weight represents unearned demand weight (0.0 = fully met, >0 = gap).
    """
    levels = student_levels(student_skills)
    gaps = {}

    for skill in benchmark_skills:
        level = level_for(levels, skill.name)
        credit = proficiency_credit(level) if level is not None else 0.0

        # Room to grow = demand * (1.0 - credit)
        gap_value = skill.weight * (1.0 - credit)

        if gap_value > 0:
            gaps[skill.name] = round(gap_value, 4)

    return gaps


def score_resource_relevance(resource_skills, student_gaps):
    """
    Scores a resource (course, project, module) against student skill gaps.

    resource_skills: list of skill names OR dict of {skill_name: coverage_weight (0-1)}
    student_gaps: dict of {skill_name: gap_weight} from calculate_student_gaps()

    Returns:
        dict: {
            'relevance_score': float (0-100 normalized score),
            'matched_gaps': list of skills targeted by this resource,
            'impact_breakdown': dict showing points addressed per skill
        }
    """
    if not student_gaps:
        return {'relevance_score': 0.0, 'matched_gaps': [], 'impact_breakdown': {}}

    # Standardize input if resource_skills is a list
    if isinstance(resource_skills, (list, tuple, set)):
        resource_skills = {skill: 1.0 for skill in resource_skills}

    matched_gaps = []
    impact_breakdown = {}
    total_impact = 0.0
    total_possible_gap = sum(student_gaps.values())

    for skill_name, gap_weight in student_gaps.items():
        if skill_name in resource_skills:
            coverage = resource_skills[skill_name]
            # Impact = how much of the gap this resource addresses
            addressed = gap_weight * coverage

            impact_breakdown[skill_name] = round(addressed, 4)
            total_impact += addressed
            matched_gaps.append(skill_name)

    # Scale relevance relative to total gap points available
    relevance_score = (
        round((total_impact / total_possible_gap) * 100.0, 2) if total_possible_gap > 0 else 0.0
    )

    return {
        'relevance_score': relevance_score,
        'matched_gaps': matched_gaps,
        'impact_breakdown': impact_breakdown,
    }


def rank_resources_by_relevance(resources, student_skills, benchmark_skills):
    """
    Utility function to score and rank multiple resources for a student.

    resources: list of dicts/objects with 'id', 'title', and 'skills'
    """
    gaps = calculate_student_gaps(student_skills, benchmark_skills)
    ranked = []

    for item in resources:
        # Supports dicts or Django model instances
        item_skills = item.get('skills') if isinstance(item, dict) else getattr(item, 'skills', [])
        result = score_resource_relevance(item_skills, gaps)

        ranked.append(
            {
                'resource': item,
                'relevance_score': result['relevance_score'],
                'matched_gaps': result['matched_gaps'],
                'impact_breakdown': result['impact_breakdown'],
            }
        )

    # Sort descending by relevance score
    ranked.sort(key=lambda x: x['relevance_score'], reverse=True)
    return ranked
