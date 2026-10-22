from django.contrib import admin

from .models import Job, JobSkill


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
