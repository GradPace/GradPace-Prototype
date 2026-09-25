# Database schema

Generated straight from `accounts/models.py` via django-extensions'
`graph_models` (Graphviz) - not hand-maintained, so it can't drift from the
actual models.

![Accounts app ER diagram](schema.svg)

## How to read it

* **Green header bar** - a model (a database table). Rows below it are that
  model's fields.
* **Bold field name** (e.g. `id`) - the primary key.
* **A dot on a line** - a real database relationship (a foreign key). The
  text on the line is the field that creates it, e.g. `role (customuser)`
  means `CustomUser.role`.
  * One dot = `ForeignKey` (points at one row in the other table).
  * A dot on *both* ends = `ManyToManyField`.
* **Open/hollow arrowhead labeled "abstract inheritance"** - not a database
  relationship at all. It just means the model's Python class inherits from
  that one (e.g. `CustomUser` extends Django's `AbstractBaseUser`). Nothing
  is stored there.
* `Group`, `Permission`, `AbstractBaseUser`, `PermissionsMixin` are Django's
  own built-in classes, pulled in automatically because `CustomUser` inherits
  from them - not something GradPace defined.

## Regenerating

After changing `accounts/models.py`, run:

```sh
make schema-diagram
```

This builds `backend/Dockerfile.dev` (the same dev image `docker-compose.dev.yml`
uses, plus Graphviz) and writes `backend/docs/schema.svg` in place. Commit the
updated SVG alongside your model changes.
