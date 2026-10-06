from django.urls import include, path

from . import views

app_name = 'core'

urlpatterns = [
    path('healthcheck/', views.health, name='health'),
    path('api/benchmarks/', include('benchmarks.urls')),
]
