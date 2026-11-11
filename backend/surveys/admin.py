from django.contrib import admin

from .models import AlumniSurveyResponse


@admin.register(AlumniSurveyResponse)
class AlumniSurveyResponseAdmin(admin.ModelAdmin):
    """Read-only. Responses are submitted by alumni through the API and
    are final. Staff can browse them here until the Survey Results
    Dashboard exists."""

    list_display = [
        'user',
        'current_job_title',
        'industry',
        'preparedness_rating',
        'platform_helpfulness_rating',
        'submitted_at',
    ]
    list_filter = ['industry', 'preparedness_rating', 'platform_helpfulness_rating', 'submitted_at']
    search_fields = ['user__email', 'current_job_title']

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
