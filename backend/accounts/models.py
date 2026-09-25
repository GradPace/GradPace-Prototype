import uuid

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.core.validators import MinValueValidator
from django.db import models


class Role(models.Model):
    """A fixed lookup table (student/alumni/admin, seeded by a data
    migration) rather than a CharField(choices=...), so new roles don't
    require a code change."""

    role_name = models.CharField(max_length=50, unique=True)
    description = models.CharField(max_length=255, blank=True, default='')

    def __str__(self):
        return self.role_name


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('Users must have an email address.')
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractBaseUser, PermissionsMixin):
    """Replaces Django's default User - UUID pk, email login, no username.
    is_active/is_staff are required by PermissionsMixin/the admin site, not
    part of the original schema notes."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=150, blank=True, default='')
    last_name = models.CharField(max_length=150, blank=True, default='')
    role = models.ForeignKey(Role, on_delete=models.SET_NULL, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = CustomUserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email


class StudentProfile(models.Model):
    """One per student CustomUser (see role). Name lives on CustomUser
    (first_name/last_name) rather than being duplicated here."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(
        CustomUser, on_delete=models.CASCADE, related_name='student_profile'
    )
    # School-issued identifier - distinct from `id`, which is just this row's
    # surrogate pk.
    student_id = models.CharField(max_length=20, unique=True)
    major = models.CharField(max_length=100)
    uni = models.CharField(max_length=150)
    location = models.CharField(max_length=150, blank=True, default='')
    readiness_score = models.FloatField(null=True, blank=True)
    graduated = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.user.email} ({self.student_id})'


class AlumniProfile(models.Model):
    """Placeholder - fields TBD beyond the pk/user link."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='alumni_profile')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.email


class AdminProfile(models.Model):
    """Placeholder - fields TBD beyond the pk/user link. Unrelated to
    CustomUser.is_staff/is_superuser, which gate Django admin access."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='admin_profile')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.email


class TakenClass(models.Model):
    """A single completed/in-progress course entry for a student, entered by
    the student themselves as part of profile completion. No uniqueness
    constraint because a student can retake a class."""

    SEMESTER_CHOICES = [
        ('fall', 'Fall'),
        ('spring', 'Spring'),
        ('summer', 'Summer'),
        ('winter', 'Winter'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        StudentProfile, on_delete=models.CASCADE, related_name='taken_classes'
    )
    course_code = models.CharField(max_length=20)
    course_name = models.CharField(max_length=150)
    semester = models.CharField(max_length=10, choices=SEMESTER_CHOICES)
    year = models.PositiveSmallIntegerField(validators=[MinValueValidator(1900)])
    # Free text, not choices - grading scales vary too much across schools.
    grade = models.CharField(max_length=5, blank=True, default='')
    credits = models.PositiveSmallIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.course_code} ({self.student.user.email})'


class Certificate(models.Model):
    """A certification/credential a student has earned, self-reported as
    part of profile completion."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(
        StudentProfile, on_delete=models.CASCADE, related_name='certificates'
    )
    name = models.CharField(max_length=150)
    issuing_organization = models.CharField(max_length=150)
    date_earned = models.DateField(null=True, blank=True)
    credential_url = models.URLField(blank=True, default='')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.name} ({self.student.user.email})'


class Skill(models.Model):
    """A skill a student has self-reported as part of profile completion.
    Unique per (student, name). Unlike classes/certificates, listing the
    same skill twice is just a duplicate, not a legitimate re-entry."""

    PROFICIENCY_CHOICES = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('expert', 'Expert'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    student = models.ForeignKey(StudentProfile, on_delete=models.CASCADE, related_name='skills')
    name = models.CharField(max_length=100)
    proficiency_level = models.CharField(
        max_length=20, choices=PROFICIENCY_CHOICES, blank=True, default=''
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']
        unique_together = ('student', 'name')

    def __str__(self):
        return f'{self.name} ({self.student.user.email})'
