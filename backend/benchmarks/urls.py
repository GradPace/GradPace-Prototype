from django.urls import path


from . import views
from .views import GapRelevanceView


urlpatterns = [
    path('calculate/', views.BenchmarkView.as_view(), name='calculate_benchmark'),
    path('me/', views.MyBenchmarkView.as_view(), name='my_benchmark'),
    path('me/best-fit/', views.BestFitJobsView.as_view(), name='my_best_fit_jobs'),
    path('roles/', views.RoleListView.as_view(), name='benchmark_roles'),
    path('roles/<str:soc_code>/', views.JobBenchmarkView.as_view(), name='job_benchmark'),
    path('skills/', views.SkillCatalogView.as_view(), name='skill_catalog'),
    path('sample/', views.SampleBenchmarkView.as_view(), name='sample_benchmark'),
    
    # Gap Relevance endpoint
     path('gap-relevance/', GapRelevanceView.as_view(), name='gap_relevance'),
]
