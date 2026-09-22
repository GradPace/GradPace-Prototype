# core/algorithms.py

def normalize_skills(raw_skills):
    """Normalize and deduplicate raw skills from various sources."""
    return [skill.strip().lower() for skill in raw_skills]

def calculate_benchmark_score(student_profile, dynamic_weights):
    """
    Evaluates a student's profile against role-specific benchmark weights.

    student_profile: dict e.g., {'skills': 75.0, 'experience': 60.0, 'networking': 40.0}
    dynamic_weights: dict e.g., {'skills': 0.40, 'experience': 0.40, 'networking': 0.20}
    """
    total_score = 0.0
    gap_breakdown = {}

    for dimension, weight in dynamic_weights.items():
        student_val = student_profile.get(dimension, 0.0)
        total_score += student_val * weight

        # Calculate gap against a target benchmark of 100
        gap = max(0.0, 100.0 - student_val)
        gap_breakdown[dimension] = {
            "current": student_val,
            "weight": weight,
            "gap": gap
        }

    return {
        "overall_readiness_score": round(total_score, 2),
        "gap_breakdown": gap_breakdown
    }