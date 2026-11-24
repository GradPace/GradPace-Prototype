# Alumni Survey API (GP-90)

Backend for the Alumni Survey (spec 3.1.1.6.2). Alumni answer questions about
their current job, the skills they use most, and how well GradPace prepared
them. Responses feed the Survey Results Dashboard (3.1.1.3.2) through the
admin-only [results endpoint](#get-apisurveyadminresults) (GP-98). Staff can
also browse individual responses read-only in Django admin under **Surveys**.

Every request needs the usual `Authorization: Bearer <access token>` header.
An interactive version is at `http://localhost:8000/api/docs/` under **survey**.

## Who can take it

Only users whose role is `alumni` (`GET /api/auth/me/` returns `"role": "alumni"`).
Everyone else gets **403**. Students get the alumni role by converting with
`POST /api/auth/convert-to-alumni/` (see
[alumni-conversion-api.md](alumni-conversion-api.md)). The survey works on
their very next request after converting, without logging in again.

Each alum can submit the survey **once**, and the submission is final.

## `GET /api/survey/alumni/`

Returns the caller's submitted response.

| Status | Meaning | Frontend should |
|---|---|---|
| 200 | Already submitted - body is the response (shape below) | show a "thanks, already submitted" state |
| 404 | Not submitted yet | show the form |
| 403 | Not an alum | hide the survey |

## `POST /api/survey/alumni/`

Submits the survey. **Every field is required**, and text answers can't be blank.

```json
{
  "current_job_title": "Junior Software Engineer",
  "industry": "software",
  "top_skills": ["Python", "Structured query language SQL"],
  "preparedness_rating": 4,
  "platform_helpfulness_rating": 5,
  "suggested_skills": ["Rust", "LLM tooling"],
  "platform_feedback": "The gap list told me exactly what to study."
}
```

| Field | Rules |
|---|---|
| `current_job_title` | text, up to 150 characters |
| `industry` | one of the values in the table below |
| `top_skills` | 1-5 different skills used most in their current role. Each must be a `name` from `GET /api/benchmark/skills/` (save the `name` and display the `label`, as on the student skill picker) |
| `preparedness_rating` | 1-5: how prepared they felt for their first job |
| `platform_helpfulness_rating` | 1-5: how much GradPace helped them prepare |
| `suggested_skills` | 1-5 newer skills that new students should focus on. Free text, up to 100 characters each, no repeats (case-insensitive). Unlike `top_skills`, these don't have to be in the catalog |
| `platform_feedback` | text, up to 2000 characters: their experience using GradPace and suggestions |

**201** returns the saved response:

```json
{
  "id": "6f1c...",
  "current_job_title": "Junior Software Engineer",
  "industry": "software",
  "top_skills": ["Python", "Structured query language SQL"],
  "preparedness_rating": 4,
  "platform_helpfulness_rating": 5,
  "suggested_skills": ["Rust", "LLM tooling"],
  "platform_feedback": "The gap list told me exactly what to study.",
  "submitted_at": "2026-11-11T15:04:05.123456Z"
}
```

**400** has two forms. Validation errors are keyed by field, in the usual DRF
shape (`{"top_skills": ["Not in the skill catalog: Foo. ..."]}`). A second
submission returns `{"detail": "Survey already submitted."}`.

The response is linked to the caller automatically, and `submitted_at` is set
by the server. Values for either one in the request body are ignored.

## `GET /api/survey/admin/results/`

Every response summed up for the admin dashboard (GP-98). **Admins only**:
logged out gets **401**, any other role **403**. The counting lives in
`surveys/results.py`.

The response is aggregates only. It never includes a name, email, user id,
response id or job title.

```json
{
  "response_count": 12,
  "latest_submitted_at": "2026-11-20T14:03:11Z",
  "ratings": {
    "preparedness_rating": {
      "average": 3.75,
      "distribution": [
        {"value": 1, "count": 0}, {"value": 2, "count": 1}, {"value": 3, "count": 3},
        {"value": 4, "count": 5}, {"value": 5, "count": 3}
      ]
    },
    "platform_helpfulness_rating": {"average": 4.1, "distribution": ["...same shape..."]}
  },
  "by_industry": [
    {"code": "software", "label": "Software / Tech", "count": 5,
     "preparedness_average": 3.8, "platform_helpfulness_average": 4.2},
    {"code": "finance", "label": "Finance / Banking", "count": 2,
     "preparedness_average": null, "platform_helpfulness_average": null}
  ],
  "top_skills": [{"name": "Amazon Web Services AWS software", "label": "AWS", "count": 4}],
  "suggested_skills": [{"skill": "Rust", "count": 3}],
  "feedback_count": 12,
  "feedback": [{"text": "The gap list told me exactly what to study.", "submitted_at": "2026-11-20T14:03:11Z"}]
}
```

| Field | Rules |
|---|---|
| `response_count`, `latest_submitted_at` | `latest_submitted_at` is `null` when there are no responses |
| `ratings.*.average` | rounded to 2 places; `null` when there are no responses |
| `ratings.*.distribution` | always all five values 1-5 in order, `0` where nobody chose it |
| `by_industry` | every industry from the table below, in that order, `0` when empty. The averages are `null` unless the industry has **at least 3 responses** (`MIN_RESPONSES_FOR_AVERAGES`), so a small industry's ratings can't be traced to one person |
| `top_skills` | every skill named, most common first (ties by label). Show `label` (the skill picker's label); `name` is the catalog name |
| `suggested_skills` | free text, so grouped ignoring case and surrounding spaces ("Rust", "rust" and " Rust " are one), shown with the most common spelling. Most common first, at most 20 |
| `feedback` | `text` and `submitted_at` only, newest first, at most 50. `feedback_count` is the total |

### Industry values

| Save as `industry` | Show in the UI |
|---|---|
| `software` | Software / Tech |
| `it_services` | IT services |
| `finance` | Finance / Banking |
| `healthcare` | Healthcare |
| `government` | Government / Defense |
| `education` | Education |
| `consulting` | Consulting |
| `manufacturing` | Manufacturing |
| `retail` | Retail / E-commerce |
| `telecom` | Telecommunications |
| `other` | Other |

## Storage notes

Responses live in `surveys.AlumniSurveyResponse`, which has one row per user
(see [schema.md](schema.md)). Unlike profile fields, survey answers are **not
encrypted at rest**, because the results dashboard needs to group and filter
by them. Changing the questions means a model change plus a migration.
