from django.urls import path

from . import views

app_name = 'surveys'

urlpatterns = [
    path('alumni/', views.AlumniSurveyView.as_view(), name='alumni-survey'),
    path('admin/results/', views.AdminSurveyResultsView.as_view(), name='admin-results'),
]
