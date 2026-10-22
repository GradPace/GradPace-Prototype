import uuid

from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import F, Q


class Job(models.Model):
    """An occupation in a given area, either taken from BLS OEWS data or
    generated to fill out the catalog. Skills hang off it as JobSkill rows
    (related_name='skills')."""

    SOURCE_CHOICES = [
        ('official', 'Official (BLS / O*NET)'),
        ('generated', 'LLM-generated'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    # BLS format (15-1252). O*NET uses 15-1252.00 - strip the suffix to join.
    soc_code = models.CharField(max_length=10, db_index=True)
    description = models.TextField(blank=True, default='')
    # The geographic area the wage/employment figures describe, e.g.
    # 'National' or a BLS metro name.
    area = models.CharField(max_length=200)
    # BLS reports wages in whole dollars. Null when BLS suppresses the value.
    median_annual_wage = models.PositiveIntegerField(null=True, blank=True)
    employment = models.PositiveIntegerField(null=True, blank=True)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.title} ({self.soc_code})'


class JobSkill(models.Model):
    """A skill a Job calls for. Unique per (job, name)."""

    # O*NET's own categories, named after the file each skill comes from.
    SKILL_TYPE_CHOICES = [
        ('essential', 'Essential'),
        ('transferable', 'Transferable'),
        ('software', 'Software'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='skills')
    name = models.CharField(max_length=100)
    skill_type = models.CharField(max_length=20, choices=SKILL_TYPE_CHOICES)
    # O*NET importance scale, 1-5.
    importance = models.FloatField(
        null=True, blank=True, validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('job', 'name')

    def __str__(self):
        return f'{self.name} ({self.job.title})'


def validate_skills_belong_to_job(job, skills):
    """A posting may only list skills of its own job. The database can't enforce
    this across the many-to-many, so JobPosting.set_skills, JobPosting.clean and
    the admin form all call this."""
    foreign = [skill.name for skill in skills if skill.job_id != job.pk]
    if foreign:
        raise ValidationError(
            {'skills': f'Skills must belong to {job.title}: {", ".join(sorted(foreign))}'}
        )


class JobPosting(models.Model):
    """A job posting for one Job, listing a subset of that job's skills. Only
    generated postings exist for now."""

    SENIORITY_CHOICES = [
        ('intern', 'Intern'),
        ('entry', 'Entry level'),
        ('mid', 'Mid level'),
        ('senior', 'Senior'),
    ]
    SOURCE_CHOICES = [
        ('generated', 'Generated'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='postings')
    title = models.CharField(max_length=200)
    company = models.CharField(max_length=200)
    # e.g. 'Norfolk, VA' or 'Remote'.
    location = models.CharField(max_length=200)
    seniority = models.CharField(max_length=20, choices=SENIORITY_CHOICES)
    salary_min = models.PositiveIntegerField(null=True, blank=True)
    salary_max = models.PositiveIntegerField(null=True, blank=True)
    description = models.TextField()
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    # Must be skills of `job` - see validate_skills_belong_to_job.
    skills = models.ManyToManyField(JobSkill, related_name='postings', blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(salary_min__isnull=True)
                | Q(salary_max__isnull=True)
                | Q(salary_min__lte=F('salary_max')),
                name='posting_salary_min_lte_max',
            ),
        ]

    def __str__(self):
        return f'{self.title} at {self.company}'

    def clean(self):
        if (
            self.salary_min is not None
            and self.salary_max is not None
            and self.salary_min > self.salary_max
        ):
            raise ValidationError({'salary_max': 'Must be at least salary_min.'})
        # Skills only exist once the posting is saved - the admin form checks the
        # unsaved selection itself.
        if self.job_id and not self._state.adding:
            validate_skills_belong_to_job(self.job, self.skills.all())

    def set_skills(self, skills):
        """Replace this (saved) posting's skills, rejecting any from another job
        before anything is written."""
        skills = list(skills)
        validate_skills_belong_to_job(self.job, skills)
        self.skills.set(skills)
