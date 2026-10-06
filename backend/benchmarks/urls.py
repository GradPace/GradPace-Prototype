from django.urls import path
from . import views

urlpatterns = [
    path('calculate/', views.run_benchmark_view, name='calculate_benchmark'),
]