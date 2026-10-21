import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


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

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='skills')
    name = models.CharField(max_length=100)
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
