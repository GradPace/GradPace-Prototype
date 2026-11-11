from django.urls import path

from . import views

app_name = 'surveys'

urlpatterns = [
    path('alumni/', views.AlumniSurveyView.as_view(), name='alumni-survey'),
]
