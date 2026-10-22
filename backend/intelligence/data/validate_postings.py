"""Validates generated_postings.json against official_jobs.json.

All companies and job postings in generated_postings.json are fictional and synthetic; any
resemblance to real organizations is coincidental.

Run from backend/ (standard library only):

    python intelligence/data/validate_postings.py

Prints every problem found and exits 1 if there are any.
"""

import argparse
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent

TOTAL_POSTINGS = 400
MIN_PER_OCCUPATION = 3
SENIORITY_WEIGHTS = {'intern': 0.10, 'entry': 0.35, 'mid': 0.35, 'senior': 0.20}
# Management roles don't hire interns and skew senior.
SENIORITY_OVERRIDES = {'11-3021': {'intern': 0, 'entry': 5, 'mid': 20, 'senior': 20}}
# Share of the occupation's national median annual wage.
SENIORITY_BANDS = {
    'intern': (0.40, 0.50),
    'entry': (0.70, 0.85),
    'mid': (0.90, 1.10),
    'senior': (1.20, 1.45),
}
SALARY_ROUNDING = 1000

LOCATION_GROUPS = {
    'hampton_roads': (
        0.92,
        [
            'Norfolk, VA',
            'Virginia Beach, VA',
            'Chesapeake, VA',
            'Newport News, VA',
            'Hampton, VA',
            'Portsmouth, VA',
            'Suffolk, VA',
        ],
    ),
    'remote': (1.00, ['Remote']),
    'northern_virginia': (1.10, ['Arlington, VA', 'Reston, VA', 'Alexandria, VA']),
    'other_virginia': (
        0.95,
        [
            'Richmond, VA',
            'Charlottesville, VA',
            'Roanoke, VA',
            'Harrisonburg, VA',
            'Lynchburg, VA',
        ],
    ),
}
LOCATION_MULTIPLIERS = {
    location: multiplier
    for multiplier, locations in LOCATION_GROUPS.values()
    for location in locations
}

# Invented names, each web-searched for a matching real business before use.
FICTIONAL_COMPANIES = {
    'Quillfeather Labs',
    'Brindlewave Software',
    'Orrinmark Systems',
    'Velquist Digital',
    'Tallowpine Technologies',
    'Thistledown Cloud',
    'Gullreach Software',
    'Wickerbay Labs',
    'Tundrabyte',
    'Cindervale Games',
    'Glimmerforge Studios',
    'Driftglass Interactive',
    'Plumhart Media',
    'Corbel & Finch Design',
    'Kestrelgate Networks',
    'Tessaline Communications',
    'Sablecrest Data Centers',
    'Graymoth Security',
    'Mirelock Cybersecurity',
    'Ironquay Defense Systems',
    'Northcairn Aerospace',
    'Brightkeel Marine Technologies',
    'Haskett Shipworks',
    'Seawick Port Services',
    'Driftanchor Logistics',
    'Oxbend Freight',
    'Marrowby Analytics',
    'Lanternfish Data Co.',
    'Coppervane Analytics',
    'Pinfeather Research Institute',
    'Stellmarch Statistics',
    'Fennimore & Vale Consulting',
    'Ravelstone Consulting',
    'Thornquill Financial Group',
    'Quintavale Bank',
    'Dunmeadow Credit Union',
    'Wrennick Mutual Insurance',
    'Tavistane Actuarial Partners',
    'Lindqvist & Harrow Actuarial',
    'Oakhollow Health Systems',
    'Halcyra Medical',
    'Fernlight Health Partners',
    'Ostrevin Biotech',
    'Velloran Semiconductor',
    'Ferrowick Electronics',
    'Brassfen Robotics',
    'Pellbrook Robotics',
    'Wendaloch Engineering',
    'Mossrun Energy',
    'Quarrystone Utilities',
    'Mapleturn Manufacturing',
    'Ambergrove Retail Group',
    'Larkmoor Commerce',
    'Halftide Hospitality Group',
    'Kindlemoss Education Tech',
    'Vantreslow College',
    'Bayreach Community College',
    'Kingsmere University',
    'Hollowell Polytechnic Institute',
    'Fallowmere Federal Services',
}

REQUIRED_FIELDS = {
    'soc_code': str,
    'title': str,
    'company': str,
    'location': str,
    'seniority': str,
    'salary_min': int,
    'salary_max': int,
    'description': str,
    'skills': list,
}
# Skills per posting by seniority: interns list a few, senior roles list many.
SKILL_RANGES = {'intern': (5, 7), 'entry': (5, 12), 'mid': (5, 12), 'senior': (9, 12)}
MIN_SENTENCES, MAX_SENTENCES = 2, 4
# Below this many software skills, an occupation can't fill "mostly software" postings.
SOFTWARE_MAJORITY_THRESHOLD = 6
SENTENCE_RE = re.compile(r'(?<=[.!?])\s+')


def largest_remainder(quotas, total):
    """Floor each quota, then hand the leftover units to the largest remainders
    (ties broken by key order)."""
    counts = {key: math.floor(quota) for key, quota in quotas.items()}
    order = list(quotas)
    leftovers = sorted(quotas, key=lambda key: (-(quotas[key] - counts[key]), order.index(key)))
    for key in leftovers[: total - sum(counts.values())]:
        counts[key] += 1
    return counts


def allocate(jobs):
    """Postings per soc_code: proportional to employment, at least MIN_PER_OCCUPATION.
    Occupations whose share falls below the minimum are pinned to it and the rest is
    re-split among the others until none fall below."""
    employment = {job['soc_code']: job['employment'] for job in jobs}
    pinned = set()
    while True:
        free = {code: emp for code, emp in employment.items() if code not in pinned}
        remaining = TOTAL_POSTINGS - MIN_PER_OCCUPATION * len(pinned)
        total_employment = sum(free.values())
        low = {
            code
            for code, emp in free.items()
            if remaining * emp / total_employment < MIN_PER_OCCUPATION
        }
        if not low:
            break
        pinned |= low
    quotas = {code: remaining * emp / total_employment for code, emp in free.items()}
    counts = largest_remainder(quotas, remaining)
    counts.update({code: MIN_PER_OCCUPATION for code in pinned})
    return counts


def seniority_mix(soc_code, count):
    if soc_code in SENIORITY_OVERRIDES:
        return dict(SENIORITY_OVERRIDES[soc_code])
    quotas = {level: count * weight for level, weight in SENIORITY_WEIGHTS.items()}
    return largest_remainder(quotas, count)


def salary_bounds(median, seniority, location):
    """The allowed salary range for a posting, before the rounding tolerance."""
    low, high = SENIORITY_BANDS[seniority]
    multiplier = LOCATION_MULTIPLIERS[location]
    return median * low * multiplier, median * high * multiplier


def validate(postings, jobs):
    errors = []
    jobs_by_code = {job['soc_code']: job for job in jobs}
    skills_by_code = {
        code: {skill['name']: skill['type'] for skill in job['skills']}
        for code, job in jobs_by_code.items()
    }

    if len(postings) != TOTAL_POSTINGS:
        errors.append(f'{len(postings)} postings, expected {TOTAL_POSTINGS}')

    seen_keys = {}
    seen_descriptions = {}
    seen_sentences = {}
    by_code = defaultdict(list)
    tolerance = SALARY_ROUNDING / 2

    for index, posting in enumerate(postings):
        label = f'#{index} {posting.get("soc_code")} {posting.get("title")!r}'
        missing = [
            field
            for field, kind in REQUIRED_FIELDS.items()
            if not isinstance(posting.get(field), kind) or isinstance(posting.get(field), bool)
        ]
        if missing:
            errors.append(f'{label}: missing or wrong type for {missing}')
            continue
        extra = set(posting) - set(REQUIRED_FIELDS)
        if extra:
            errors.append(f'{label}: unexpected fields {sorted(extra)}')

        code = posting['soc_code']
        if code not in jobs_by_code:
            errors.append(f'{label}: soc_code not in official_jobs.json')
            continue
        by_code[code].append(posting)

        seniority = posting['seniority']
        if seniority not in SENIORITY_BANDS:
            errors.append(f'{label}: invalid seniority {seniority!r}')
        if posting['company'] not in FICTIONAL_COMPANIES:
            errors.append(f'{label}: company {posting["company"]!r} not in FICTIONAL_COMPANIES')
        if posting['location'] not in LOCATION_MULTIPLIERS:
            errors.append(f'{label}: location {posting["location"]!r} not allowed')

        salary_min, salary_max = posting['salary_min'], posting['salary_max']
        if salary_min <= 0 or salary_max <= 0:
            errors.append(f'{label}: salaries must be positive')
        if salary_min > salary_max:
            errors.append(f'{label}: salary_min {salary_min} > salary_max {salary_max}')
        if seniority in SENIORITY_BANDS and posting['location'] in LOCATION_MULTIPLIERS:
            low, high = salary_bounds(
                jobs_by_code[code]['median_annual_wage'], seniority, posting['location']
            )
            if salary_min < low - tolerance or salary_max > high + tolerance:
                errors.append(
                    f'{label}: salary {salary_min}-{salary_max} outside {seniority} band '
                    f'{low:.0f}-{high:.0f} for {posting["location"]}'
                )

        skills = posting['skills']
        min_skills, max_skills = SKILL_RANGES.get(seniority, (5, 12))
        if not min_skills <= len(skills) <= max_skills:
            errors.append(
                f'{label}: {len(skills)} skills, expected {min_skills}-{max_skills} for {seniority}'
            )
        if len(skills) != len(set(skills)):
            errors.append(f'{label}: duplicate skill names')
        unknown = [name for name in skills if name not in skills_by_code[code]]
        if unknown:
            errors.append(f'{label}: skills not on {code}: {unknown}')
        job_software = sum(1 for kind in skills_by_code[code].values() if kind == 'software')
        posting_software = sum(1 for name in skills if skills_by_code[code].get(name) == 'software')
        if job_software >= SOFTWARE_MAJORITY_THRESHOLD and posting_software * 2 < len(skills):
            errors.append(f'{label}: only {posting_software}/{len(skills)} skills are software')

        key = (code, posting['title'], posting['company'], posting['location'])
        if key in seen_keys:
            errors.append(f'{label}: duplicate of #{seen_keys[key]} (same title/company/location)')
        seen_keys.setdefault(key, index)

        description = posting['description'].strip()
        if description in seen_descriptions:
            errors.append(f'{label}: description duplicates #{seen_descriptions[description]}')
        seen_descriptions.setdefault(description, index)
        sentences = [s for s in SENTENCE_RE.split(description) if s]
        if not MIN_SENTENCES <= len(sentences) <= MAX_SENTENCES:
            errors.append(
                f'{label}: {len(sentences)} sentences, expected {MIN_SENTENCES}-{MAX_SENTENCES}'
            )
        for sentence in sentences:
            normalized = sentence.strip().lower()
            if normalized in seen_sentences and seen_sentences[normalized] != index:
                errors.append(
                    f'{label}: sentence reused from #{seen_sentences[normalized]}: {sentence!r}'
                )
            seen_sentences.setdefault(normalized, index)

    expected = allocate(jobs)
    for code, count in expected.items():
        actual = by_code.get(code, [])
        if len(actual) != count:
            errors.append(f'{code}: {len(actual)} postings, expected {count}')
            continue
        mix = Counter(posting['seniority'] for posting in actual)
        expected_mix = seniority_mix(code, count)
        if any(mix.get(level, 0) != n for level, n in expected_mix.items()):
            errors.append(f'{code}: seniority mix {dict(mix)}, expected {expected_mix}')

    return errors


def main():
    parser = argparse.ArgumentParser(description='Validate generated_postings.json.')
    parser.add_argument('--postings', type=Path, default=DATA_DIR / 'generated_postings.json')
    parser.add_argument('--jobs', type=Path, default=DATA_DIR / 'official_jobs.json')
    args = parser.parse_args()

    postings = json.loads(args.postings.read_text())
    jobs = json.loads(args.jobs.read_text())
    errors = validate(postings, jobs)
    for error in errors:
        print(error)
    if errors:
        print(f'FAILED: {len(errors)} problem(s)')
        sys.exit(1)
    print(f'OK: {len(postings)} postings across {len({p["soc_code"] for p in postings})} jobs')


if __name__ == '__main__':
    main()
