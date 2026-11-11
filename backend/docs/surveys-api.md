# Alumni Survey API (GP-90)

Backend for the Alumni Survey (spec 3.1.1.6.2). Alumni answer questions about
their current job, the skills they use most, and how well GradPace prepared
them. Responses are stored for the Survey Results Dashboard (3.1.1.3.2), which
doesn't have an endpoint yet. Until it does, staff can browse responses
read-only in Django admin under **Surveys**.

Every request needs the usual `Authorization: Bearer <access token>` header.
An interactive version is at `http://localhost:8000/api/docs/` under **survey**.

## Who can take it

Only users whose role is `alumni` (`GET /api/auth/me/` returns `"role": "alumni"`).
Everyone else gets **403**. This endpoint doesn't decide who is an alum. The
role is set elsewhere (currently by an admin).

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
