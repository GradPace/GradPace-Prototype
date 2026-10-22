from django import forms
from django.contrib import admin

from .models import Job, JobPosting, JobSkill, validate_skills_belong_to_job


class JobSkillInline(admin.TabularInline):
    model = JobSkill
    fields = ['name', 'skill_type', 'importance']
    extra = 0


@admin.register(Job)
class JobAdmin(admin.ModelAdmin):
    inlines = [JobSkillInline]


@admin.register(JobSkill)
class JobSkillAdmin(admin.ModelAdmin):
    list_display = ['name', 'job', 'skill_type', 'importance']
    list_filter = ['skill_type']


class JobPostingAdminForm(forms.ModelForm):
    """JobPosting.clean can't see skills picked on an unsaved form, so check the
    selection against the chosen job here."""

    class Meta:
        model = JobPosting
        fields = '__all__'

    def clean(self):
        cleaned_data = super().clean()
        job = cleaned_data.get('job')
        skills = cleaned_data.get('skills')
        if job and skills:
            validate_skills_belong_to_job(job, skills)
        return cleaned_data


@admin.register(JobPosting)
class JobPostingAdmin(admin.ModelAdmin):
    form = JobPostingAdminForm
    list_display = ['job', 'title', 'seniority', 'company']
    list_filter = ['seniority', 'job']
    filter_horizontal = ['skills']
