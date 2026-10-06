from django.urls import path

from . import views

urlpatterns = [
    path('calculate/', views.BenchmarkView.as_view(), name='calculate_benchmark'),
    path('sample/', views.SampleBenchmarkView.as_view(), name='sample_benchmark'),
]
