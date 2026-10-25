# Readiness & benchmark API (GP-66)

What the frontend needs to build skill picking, the readiness gauge, gaps /
recommendations, and best-fit jobs. Every endpoint needs the usual
`Authorization: Bearer <access token>` header. Interactive versions of all of
these are at `http://localhost:8000/api/docs/` under **benchmark** and **auth**.

## How it fits together

1. **Pick a target job** - `GET /api/benchmark/roles/` for the list, then save it
   with `PATCH /api/auth/profile/` `{"target_job": "15-1252"}`.
2. **Pick skills** - `GET /api/benchmark/skills/?role=15-1252` for that job's
   skills, then save each one with `POST /api/auth/profile/skills/`.
3. **Show readiness** - `GET /api/benchmark/me/` for the score (gauge) and the
   ranked gaps (recommendations).
4. **Show best-fit jobs** - `GET /api/benchmark/me/best-fit/`.

**Proficiency** is stored as text and scored as 1-4:

| Show in the UI | Save as `proficiency_level` | Counts for |
|---|---|---|
| 1 - Beginner | `"beginner"` | 25% of the skill |
| 2 - Intermediate | `"intermediate"` | 50% |
| 3 - Advanced | `"advanced"` | 75% |
| 4 - Expert | `"expert"` | 100% |

Responses report a student's level as the number (`your_level: 3`), or `null`
if they don't have the skill.

**Skill names:** always save a skill's `name` (the exact O\*NET name, e.g.
`"Structured query language SQL"`), and display its `label` (`"SQL"`). Saving
the label also matches, but `name` is the safe choice.

## Jobs

### `GET /api/benchmark/roles/`

The 24 jobs, alphabetical. `posting_count` is how much data the job has - low
counts mean a rougher benchmark.

```json
[
  {"soc_code": "15-2011", "title": "Actuaries", "posting_count": 3},
  {"soc_code": "15-1252", "title": "Software Developers", "posting_count": 113}
]
```

### `GET /api/benchmark/roles/<soc_code>/`

One job's benchmark - "what employers want". `weight` is the share of postings
listing the skill. 404 for an unknown code.

```json
{
  "role": {"soc_code": "15-1252", "title": "Software Developers"},
  "postings_used": 51,
  "seniorities_used": "intern/entry",
  "skills": [
    {"name": "Programming", "label": "Programming", "skill_type": "transferable", "weight": 0.9608},
    {"name": "Git", "label": "Git", "skill_type": "software", "weight": 0.7843}
  ]
}
```

## Skills

### `GET /api/benchmark/skills/` and `GET /api/benchmark/skills/?role=<soc_code>`

The skills to pick from. With `?role=`, only that job's (most in-demand first) -
use this for the picker. Without it, every skill in any job's benchmark (133).
400 for an unknown role.

```json
[
  {"name": "Programming", "label": "Programming", "skill_type": "transferable", "job_count": 1, "demand": 0.961},
  {"name": "Structured query language SQL", "label": "SQL", "skill_type": "software", "job_count": 1, "demand": 0.353}
]
```

`skill_type` is O\*NET's category - suggested display names: `software` ->
"Technical tools", `transferable` -> "Transferable skills", `essential` ->
"Core skills".

### Saving a student's skills (existing endpoints)

| | |
|---|---|
| List | `GET /api/auth/profile/skills/` |
| Add | `POST /api/auth/profile/skills/` `{"name": "Docker", "proficiency_level": "advanced"}` |
| Change level | `PATCH /api/auth/profile/skills/<id>/` `{"proficiency_level": "expert"}` |
| Remove | `DELETE /api/auth/profile/skills/<id>/` |

Adding the same skill twice is a 400 (one row per skill per student).

## Target job (on the profile)

`GET /api/auth/profile/` now includes `target_job` (SOC code or `null`) and
`target_job_title`. Set or clear it with `POST`/`PATCH /api/auth/profile/`
`{"target_job": "15-1252"}` / `{"target_job": null}`. Unknown codes are a 400.

## Readiness

### `GET /api/benchmark/me/`

The student's readiness for their target job. Add `?role=<soc_code>` to look at
a different job without changing anything. 400 if there's no `?role=` and no
target job saved; 404 if the user has no student profile yet.

The profile's `readiness_score` is only updated when this is called for the
target job (`saved_to_profile: true`) - so **call this on dashboard load**
rather than reading `readiness_score` off the profile, which can be stale after
skills change.

```json
{
  "overall_readiness_score": 22.68,
  "role": {"soc_code": "15-2051", "title": "Data Scientists"},
  "benchmark": {"postings_used": 17, "seniorities_used": "all"},
  "saved_to_profile": true,
  "gap_breakdown": {
    "software": {"current": 24.76, "weight": 0.79, "gap": 75.24},
    "essential": {"current": 5.0, "weight": 0.155, "gap": 95.0},
    "transferable": {"current": 42.85, "weight": 0.054, "gap": 57.15}
  },
  "flagged_gaps": [
    {
      "dimension": "software",
      "gap": 75.24,
      "points_available": 59.49,
      "top_unmet_skills": [
        {"name": "pandas", "label": "pandas", "demand": 0.765, "your_level": null, "met": false}
      ]
    }
  ],
  "skills": {
    "software": [
      {"name": "Python", "label": "Python", "demand": 1.0, "your_level": 3, "met": false}
    ]
  }
}
```

- `overall_readiness_score` (0-100) - the gauge.
- `benchmark.postings_used` - for a "based on N postings" note.
- `flagged_gaps` - **already sorted by what to work on first**: each skill type
  with a gap, ordered by how many overall points closing it would add, each with
  its top 5 skills to improve (missing ones first, then low levels). This is
  what recommendations should be built from.
- `skills` - every benchmark skill per type with the student's level, most
  in-demand first - for a full "you vs. the market" view.
- `gap_breakdown` - the per-type scores and weights from the GP-40 formula.

### `GET /api/benchmark/me/best-fit/`

The student's readiness for all 24 jobs, best match first. Doesn't change
anything. `limited_data: true` means the benchmark comes from under 10
postings - those are ranked after the rest and should be shown with a caveat.

```json
[
  {
    "role": {"soc_code": "15-1252", "title": "Software Developers"},
    "overall_readiness_score": 37.58,
    "postings_used": 51,
    "limited_data": false,
    "top_unmet_skills": [
      {"name": "Git", "label": "Git", "demand": 0.784, "your_level": 2, "met": false}
    ]
  }
]
```

## Demo students

`uv run manage.py seed_demo_students --password <password>` (after `migrate`)
creates four ODU / Norfolk students targeting Software Developers - Alex
(about 71), Priya (about 33), Marcus (about 7), and Jordan (about 13, but about 43
for Data Scientists - shows off best-fit). Logins are
`demo.alex@example.com`, `demo.priya@example.com`, `demo.marcus@example.com`,
`demo.jordan@example.com`. Safe to rerun: it resets them.
