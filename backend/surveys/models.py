import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q

RATING_VALIDATORS = [MinValueValidator(1), MaxValueValidator(5)]


class AlumniSurveyResponse(models.Model):
    """One alum's answers to the Alumni Survey (spec 3.1.1.6.2). One per
    user, final once submitted. The OneToOne enforces that in the database.

    Nothing here is encrypted at rest (unlike accounts/fields.py's fields):
    the Survey Results Dashboard needs to group and filter by these values,
    which encrypted columns can't do."""

    INDUSTRY_CHOICES = [
        ('software', 'Software / Tech'),
        ('it_services', 'IT services'),
        ('finance', 'Finance / Banking'),
        ('healthcare', 'Healthcare'),
        ('government', 'Government / Defense'),
        ('education', 'Education'),
        ('consulting', 'Consulting'),
        ('manufacturing', 'Manufacturing'),
        ('retail', 'Retail / E-commerce'),
        ('telecom', 'Telecommunications'),
        ('other', 'Other'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='alumni_survey'
    )
    current_job_title = models.CharField(max_length=150)
    industry = models.CharField(max_length=50, choices=INDUSTRY_CHOICES)
    # Skills used most in their current role. Names from the skill catalog
    # (benchmarks/catalog.py). The catalog is computed, not a table, so this
    # can't be a foreign key; the serializer checks each name instead.
    top_skills = models.JSONField(default=list)
    # How prepared they felt for their first job, 1-5.
    preparedness_rating = models.PositiveSmallIntegerField(validators=RATING_VALIDATORS)
    # How much GradPace helped them get there, 1-5.
    platform_helpfulness_rating = models.PositiveSmallIntegerField(validators=RATING_VALIDATORS)
    # Newer skills they'd tell current students to focus on. Free text, not
    # catalog names. The point is skills the catalog may not have yet.
    suggested_skills = models.JSONField(default=list)
    platform_feedback = models.TextField()
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-submitted_at']
        constraints = [
            models.CheckConstraint(
                condition=Q(preparedness_rating__gte=1, preparedness_rating__lte=5),
                name='survey_preparedness_rating_1_to_5',
            ),
            models.CheckConstraint(
                condition=Q(platform_helpfulness_rating__gte=1, platform_helpfulness_rating__lte=5),
                name='survey_platform_helpfulness_rating_1_to_5',
            ),
        ]

    def __str__(self):
        return f'Alumni survey ({self.user.email})'
