# Intelligence seed data

All companies and job postings in `generated_postings.json` are fictional and synthetic; any
resemblance to real organizations is coincidental.

| File | What it is |
|---|---|
| `official_jobs.json` | 24 tech occupations from BLS OEWS (May 2025, national) joined with O\*NET 31.0 skills. |
| `build_official_jobs.py` | One-off script that builds `official_jobs.json` from the raw BLS and O\*NET files. |
| `generated_postings.json` | 400 synthetic job postings, each tied to an occupation by `soc_code`. |
| `validate_postings.py` | Checks `generated_postings.json` against `official_jobs.json`. |

## How generated_postings.json was made

- **Allocation:** 400 postings are split across the 24 occupations in proportion to national
  employment, with a minimum of 3 each. An occupation whose share falls below 3 is pinned at 3
  and the rest is re-split. Largest-remainder rounding makes the total exactly 400
  (`allocate()` in `validate_postings.py`).
- **Seniority mix:** 10% intern, 35% entry, 35% mid and 20% senior per occupation, again with
  largest-remainder rounding. The exception is 11-3021 (Computer and Information Systems
  Managers), which is fixed at 0/5/20/20, because management roles don't hire interns and skew
  senior.
- **Locations and salaries:** salaries are anchored on the occupation's national median wage.
  Each salary range is median × seniority band × location multiplier, rounded to $1,000.

  | Location | Share | Multiplier |
  |---|---|---|
  | Hampton Roads (Norfolk, Virginia Beach, Chesapeake, Newport News, Hampton, Portsmouth, Suffolk) | ~70% | ×0.92 |
  | Remote | ~20% | ×1.00 |
  | Northern Virginia (Arlington, Reston, Alexandria) | ~5% | ×1.10 |
  | Other Virginia (Richmond, Charlottesville, Roanoke, Harrisonburg, Lynchburg) | ~5% | ×0.95 |

  | Seniority | Band (share of median) |
  |---|---|
  | Intern | 0.40–0.50 |
  | Entry | 0.70–0.85 |
  | Mid | 0.90–1.10 |
  | Senior | 1.20–1.45 |

- **Skills:** every skill is an exact name from that occupation's skills in
  `official_jobs.json`.
  - Interns list 5–7 skills, entry and mid roles 5–12, and senior roles 9–12.
  - At least half are software skills whenever the occupation has 6 or more software skills.
  - Three occupations have only 3–4 software skills (11-3021, 17-2072, 25-1021); their
    postings use all of them plus essential and transferable skills.
- **Text:** titles and 2–4 sentence descriptions were generated offline by an LLM (Claude),
  one occupation at a time; nothing is generated at runtime. Companies come from the fixed
  `FICTIONAL_COMPANIES` list in `validate_postings.py`, each name checked against real
  businesses. The file must pass `validate_postings.py`.

## Rebuilding and validating

Run from `backend/`:

```sh
# official_jobs.json (needs the raw BLS and O*NET files in the --raw-dir directory)
uv run --with openpyxl python intelligence/data/build_official_jobs.py --raw-dir /path/to/raw-data

# check generated_postings.json
uv run python intelligence/data/validate_postings.py

# load both files into the database (safe to rerun; --dry-run validates only)
uv run manage.py seed_jobs
```

`validate_postings.py` checks:
- the per-occupation allocation (400 total, proportional to employment, minimum 3) and
  seniority mix
- that every skill exists on the posting's occupation
- that salaries fall inside the seniority band and location multiplier
- that every company is on the fictional-company list
- that there are no duplicate postings or reused description sentences

## Attribution

Occupation skills data comes from the O\*NET 31.0 Database by the U.S. Department of Labor,
Employment and Training Administration (USDOL/ETA), used under the CC BY 4.0 license. Employment
and wage data comes from the U.S. Bureau of Labor Statistics Occupational Employment and Wage
Statistics program.
