# Database schema

## Relationships

Generated from the models by `make schema-docs`. Read each FK row as
"**`From.field`** points at **`To`**". In the diagram, the line is labeled
with the FK field and the table on the `o{` ("many") end holds the FK column.

Crow's-foot symbols: `||` exactly one, `o|` zero or one, `o{` zero or many.
`PK` primary key, `FK` foreign key, `UK` unique.

<!-- schema:start -->

### Foreign keys

| From (holds the FK column) | Field | Points at | Type | If the target is deleted |
|---|---|---|---|---|
| `AdminProfile` | `user` | `CustomUser` | one-to-one | row deleted |
| `AlumniProfile` | `user` | `CustomUser` | one-to-one | row deleted |
| `Certificate` | `student` | `StudentProfile` | many Certificate to one StudentProfile | row deleted |
| `CustomUser` | `role` | `Role` | many CustomUser to one Role (optional) | FK set to NULL |
| `JobPosting` | `job` | `Job` | many JobPosting to one Job | row deleted |
| `JobPosting` | `skills` | `JobSkill` | many-to-many | link row removed |
| `JobSkill` | `job` | `Job` | many JobSkill to one Job | row deleted |
| `Skill` | `student` | `StudentProfile` | many Skill to one StudentProfile | row deleted |
| `StudentProfile` | `target_job` | `Job` | many StudentProfile to one Job (optional) | FK set to NULL |
| `StudentProfile` | `user` | `CustomUser` | one-to-one | row deleted |
| `TakenClass` | `student` | `StudentProfile` | many TakenClass to one StudentProfile | row deleted |

### Diagram

```mermaid
erDiagram
    CustomUser ||--o| AdminProfile : "AdminProfile.user"
    CustomUser ||--o| AlumniProfile : "AlumniProfile.user"
    CustomUser ||--o| StudentProfile : "StudentProfile.user"
    Job |o--o{ StudentProfile : "StudentProfile.target_job"
    Job ||--o{ JobPosting : "JobPosting.job"
    Job ||--o{ JobSkill : "JobSkill.job"
    JobPosting }o--o{ JobSkill : "JobPosting.skills"
    Role |o--o{ CustomUser : "CustomUser.role"
    StudentProfile ||--o{ Certificate : "Certificate.student"
    StudentProfile ||--o{ Skill : "Skill.student"
    StudentProfile ||--o{ TakenClass : "TakenClass.student"

    Role {
        BigAutoField id PK
        CharField role_name UK
        CharField description
    }
    CustomUser {
        CharField password
        DateTimeField last_login
        BooleanField is_superuser
        UUIDField id PK
        CharField email UK
        TextField first_name
        TextField last_name
        BigAutoField role_id FK
        DateTimeField created_at
        BooleanField is_active
        BooleanField is_staff
    }
    StudentProfile {
        UUIDField id PK
        UUIDField user_id FK, UK
        CharField student_id UK
        TextField major
        TextField uni
        TextField location
        FloatField readiness_score
        UUIDField target_job_id FK
        BooleanField graduated
        DateTimeField updated_at
    }
    AlumniProfile {
        UUIDField id PK
        UUIDField user_id FK, UK
        DateTimeField updated_at
    }
    AdminProfile {
        UUIDField id PK
        UUIDField user_id FK, UK
        DateTimeField updated_at
    }
    TakenClass {
        UUIDField id PK
        UUIDField student_id FK
        CharField course_code
        CharField course_name
        CharField semester
        PositiveSmallIntegerField year
        TextField grade
        PositiveSmallIntegerField credits
        DateTimeField created_at
        DateTimeField updated_at
    }
    Certificate {
        UUIDField id PK
        UUIDField student_id FK
        CharField name
        CharField issuing_organization
        DateField date_earned
        TextField credential_url
        DateTimeField created_at
        DateTimeField updated_at
    }
    Skill {
        UUIDField id PK
        UUIDField student_id FK
        CharField name
        CharField proficiency_level
        DateTimeField created_at
        DateTimeField updated_at
    }
    Job {
        UUIDField id PK
        CharField title
        CharField soc_code
        TextField description
        CharField area
        PositiveIntegerField median_annual_wage
        PositiveIntegerField employment
        CharField source
        DateTimeField created_at
        DateTimeField updated_at
    }
    JobSkill {
        UUIDField id PK
        UUIDField job_id FK
        CharField name
        CharField skill_type
        FloatField importance
        DateTimeField created_at
        DateTimeField updated_at
    }
    JobPosting {
        UUIDField id PK
        UUIDField job_id FK
        CharField title
        CharField company
        CharField location
        CharField seniority
        PositiveIntegerField salary_min
        PositiveIntegerField salary_max
        TextField description
        CharField source
        DateTimeField created_at
        DateTimeField updated_at
    }
```

<!-- schema:end -->

## Regenerating

After changing any model, run:

```sh
make schema-docs
```

`uv run manage.py schema_docs --check` fails if they are out of date.
