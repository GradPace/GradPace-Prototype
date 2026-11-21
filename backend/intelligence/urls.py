from django.urls import path

from . import views

urlpatterns = [
    path(
        'events/sample/',
        views.SampleEventSuggestionsView.as_view(),
        name='sample_event_suggestions',
    ),
    path('places/', views.PlaceSearchView.as_view(), name='place_search'),
]
