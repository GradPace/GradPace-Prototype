# Alumni Conversion API

Backend for Alumni Conversion (spec 3.1.1.6.1). A student enters their
graduation date and becomes an alum. After converting they can take the
[Alumni Survey](surveys-api.md).

Every request needs the usual `Authorization: Bearer <access token>` header.
An interactive version is at `http://localhost:8000/api/docs/` under **auth**.

## For the frontend

- **When to show "Convert to Alumni"** (FR-01): when `GET /api/auth/me/`
  returns `"role": "student"`. Any other role gets a 403 from the endpoint.
- **Ask for a graduation date** (FR-02): it can't be in the future. Set the
  date picker's `max` to today. The backend checks it too.
- **Confirm before sending** (FR-03): show an "Are you sure?" dialog first.
  The request itself is the confirmation, and there's no undo for students.
- **After it succeeds:** fetch `/api/auth/me/` again (the role is now
  `"alumni"`) to swap the button for the survey link. The user doesn't need to
  log in again. Their profile, classes, skills and certificates are all still
  there (FR-04).

## `POST /api/auth/convert-to-alumni/`

```json
{ "graduation_date": "2026-05-09" }
```

| Field | Rules |
|---|---|
| `graduation_date` | required, `YYYY-MM-DD`, not in the future, year 1900 or later. "Today" is measured in Eastern time (the server's time zone) |

**200** - converted:

```json
{ "role": "alumni", "graduation_date": "2026-05-09" }
```

| Status | Meaning |
|---|---|
| 200 | Converted |
| 400 | Graduation date missing, badly formatted, in the future, or before 1900. Errors are keyed by field: `{"graduation_date": ["Graduation date cannot be in the future."]}` |
| 401 | Not logged in |
| 403 | Not a student. This includes alumni, so converting twice gives a 403 |
| 404 | The student hasn't set up their profile yet (`/api/auth/profile/` returns 404 too) |

## What changes

All of the following happen together, or none of them do:

1. The account's role changes from `student` to `alumni`.
2. `graduated` on their student profile becomes `true`.
3. Their `AlumniProfile` is created, holding `graduation_date`. If an admin
   already made one by hand, that one gets the date instead.

Nothing is deleted. `graduated` can only be changed this way: profile
create and update ignore it, so it always matches the role.

Students can't convert back. An admin can change the role in Django admin if
needed.
