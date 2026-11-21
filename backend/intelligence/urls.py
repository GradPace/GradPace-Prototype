from django.urls import path

from . import views

urlpatterns = [
    path(
        'events/sample/',
        views.SampleEventSuggestionsView.as_view(),
        name='sample_event_suggestions',
    ),
    path('places/', views.PlaceSearchView.as_view(), name='place_search'),
    path('events/', views.EventListView.as_view(), name='event_list'),
    path(
        'events/recommendation/',
        views.EventRecommendationView.as_view(),
        name='event_recommendation',
    ),
    path('events/<slug:event_id>/chat/', views.EventChatView.as_view(), name='event_chat'),
]
