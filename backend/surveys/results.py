"""Survey Results Dashboard (spec 3.1.1.3.2, GP-98): the Alumni Survey
responses summed up for admins. Aggregates only - no response here carries a
name, email, user id, response id or job title; only the fields read below
ever leave the database.
"""

from collections import Counter, defaultdict

from django.db.models import Avg, Count, Max

from benchmarks.catalog import label_for

from .models import AlumniSurveyResponse

# Per-industry averages are hidden (null) below this many responses, so a
# small industry's numbers can't be traced back to one or two alumni.
MIN_RESPONSES_FOR_AVERAGES = 3
MAX_SUGGESTED_SKILLS = 20
MAX_FEEDBACK = 50
RATING_VALUES = range(1, 6)
RATING_FIELDS = ('preparedness_rating', 'platform_helpfulness_rating')


def _average(value):
    return None if value is None else round(value, 2)


def _rating_summary(responses, field):
    counts = dict(responses.values_list(field).annotate(n=Count('id')).order_by())
    return {
        'average': _average(responses.aggregate(average=Avg(field))['average']),
        # Every value 1-5, even with no responses, so charts have fixed bars.
        'distribution': [
            {'value': value, 'count': counts.get(value, 0)} for value in RATING_VALUES
        ],
    }


def _by_industry(responses):
    rows = {
        row['industry']: row
        for row in responses.values('industry')
        .annotate(
            count=Count('id'),
            preparedness=Avg('preparedness_rating'),
            helpfulness=Avg('platform_helpfulness_rating'),
        )
        .order_by()
    }
    # Every choice in order, then any stored code that isn't one (the
    # database doesn't enforce choices), so the counts add up to the total.
    industries = list(AlumniSurveyResponse.INDUSTRY_CHOICES)
    known = {code for code, _ in industries}
    industries += [(code, code) for code in sorted(rows) if code not in known]

    results = []
    for code, label in industries:
        row = rows.get(code, {})
        count = row.get('count', 0)
        enough = count >= MIN_RESPONSES_FOR_AVERAGES
        results.append(
            {
                'code': code,
                'label': label,
                'count': count,
                'preparedness_average': _average(row['preparedness']) if enough else None,
                'platform_helpfulness_average': _average(row['helpfulness']) if enough else None,
            }
        )
    return results


def _most_common(counts):
    """(key, count) pairs, most common first, ties alphabetical."""
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))


def _top_skills(skill_lists):
    """Catalog names, so each is shown with the same label as the skill picker."""
    counts = Counter(name for names in skill_lists for name in names)
    return [
        {'name': name, 'label': label_for(name), 'count': count}
        for name, count in sorted(counts.items(), key=lambda item: (-item[1], label_for(item[0])))
    ]


def _suggested_skills(skill_lists):
    """Free text, so "Rust", "rust" and " Rust " are one skill, shown with
    the spelling alumni used most."""
    spellings = defaultdict(Counter)
    for skills in skill_lists:
        for skill in skills:
            spelling = skill.strip()
            if spelling:
                spellings[spelling.casefold()][spelling] += 1
    grouped = {_most_common(variants)[0][0]: variants.total() for variants in spellings.values()}
    return [
        {'skill': skill, 'count': count}
        for skill, count in _most_common(grouped)[:MAX_SUGGESTED_SKILLS]
    ]


def _feedback(responses):
    # The API strips and requires it, so blank only comes from rows made by hand.
    with_feedback = responses.exclude(platform_feedback='')
    newest = with_feedback.order_by('-submitted_at', '-id').values_list(
        'platform_feedback', 'submitted_at'
    )[:MAX_FEEDBACK]
    return with_feedback.count(), [
        {'text': text, 'submitted_at': submitted_at} for text, submitted_at in newest
    ]


def report():
    responses = AlumniSurveyResponse.objects.all()
    totals = responses.aggregate(count=Count('id'), latest=Max('submitted_at'))
    skills = list(responses.values_list('top_skills', 'suggested_skills'))
    feedback_count, feedback = _feedback(responses)
    return {
        'response_count': totals['count'],
        'latest_submitted_at': totals['latest'],
        'ratings': {field: _rating_summary(responses, field) for field in RATING_FIELDS},
        'by_industry': _by_industry(responses),
        'top_skills': _top_skills(top for top, _ in skills),
        'suggested_skills': _suggested_skills(suggested for _, suggested in skills),
        'feedback_count': feedback_count,
        'feedback': feedback,
    }
