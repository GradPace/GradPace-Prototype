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
# by_industry's row for stored codes that aren't an industry choice.
UNSPECIFIED_CODE = ''
UNSPECIFIED_LABEL = 'Unspecified'


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
    choices = AlumniSurveyResponse.INDUSTRY_CHOICES
    results = [
        _industry_row(code, label, [rows[code]] if code in rows else []) for code, label in choices
    ]
    # The database doesn't enforce choices, so a hand-made row can hold
    # anything, blank included. All of those share one "Unspecified" row, so
    # nothing shows blank or as a raw code and the counts add up to the total.
    known = {code for code, _ in choices}
    unlisted = [row for code, row in rows.items() if code not in known]
    if unlisted:
        results.append(_industry_row(UNSPECIFIED_CODE, UNSPECIFIED_LABEL, unlisted))
    return results


def _industry_row(code, label, groups):
    """One by_industry row from one or more grouped rows; averages weighted
    by each group's count, and hidden below MIN_RESPONSES_FOR_AVERAGES."""
    count = sum(group['count'] for group in groups)
    enough = count >= MIN_RESPONSES_FOR_AVERAGES

    def weighted(key):
        if not enough:
            return None
        return _average(sum(group[key] * group['count'] for group in groups) / count)

    return {
        'code': code,
        'label': label,
        'count': count,
        'preparedness_average': weighted('preparedness'),
        'platform_helpfulness_average': weighted('helpfulness'),
    }


def _most_common(counts):
    """(key, count) pairs, most common first, ties alphabetical."""
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))


def _once_each(skills):
    """One response's skills, stripped, blanks dropped, and each listed once
    (ignoring case) - so counts are alumni, never more than the responses.
    The API already rejects repeats; this covers rows made by hand."""
    seen = {}
    for skill in skills:
        spelling = skill.strip()
        if spelling:
            seen.setdefault(spelling.casefold(), spelling)
    return seen.values()


def _top_skills(skill_lists):
    """Catalog names, so each is shown with the same label as the skill picker."""
    counts = Counter(name for names in skill_lists for name in _once_each(names))
    return [
        {'name': name, 'label': label_for(name), 'count': count}
        for name, count in sorted(counts.items(), key=lambda item: (-item[1], label_for(item[0])))
    ]


def _suggested_skills(skill_lists):
    """Free text, so "Rust", "rust" and " Rust " are one skill, shown with
    the spelling alumni used most."""
    spellings = defaultdict(Counter)
    for skills in skill_lists:
        for spelling in _once_each(skills):
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
    # Counts and averages run in the database; only the two skill lists come
    # into Python. Fine at this scale - cache this if the dashboard gets busy.
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
