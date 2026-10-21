from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

# Generating the schema walks every view and serializer - the most expensive
# GET we serve - and it only changes on deploy, so cache it outside DEBUG
# (where it'd hide schema changes until the cache expires). Vary on Accept so
# a JSON and a YAML request don't get each other's cached response.
schema_view = SpectacularAPIView.as_view()
if not settings.DEBUG:
    schema_view = cache_page(60 * 60)(vary_on_headers('Accept')(schema_view))

urlpatterns = [
    path('admin/', admin.site.urls),
    path('core/', include('core.urls')),
    path('api/auth/', include('accounts.urls')),
    path('api/benchmark/', include('benchmarks.urls')),
    path('api/schema/', schema_view, name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='docs'),
]
