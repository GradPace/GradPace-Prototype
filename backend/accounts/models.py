from django.conf import settings
from django.db import models


class StudentProfile(models.Model):
    """Extends the built-in User with student-specific fields. Name lives on
    User (first_name/last_name) rather than being duplicated here."""

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="student_profile"
    )
    student_id = models.CharField(max_length=20, unique=True)
    major = models.CharField(max_length=100)
    minor = models.CharField(max_length=100, blank=True, default="")
    graduation_year = models.PositiveIntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} ({self.student_id})"
