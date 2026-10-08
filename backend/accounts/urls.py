from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from . import views

app_name = 'accounts'

urlpatterns = [
    path('register/', views.RegisterView.as_view(), name='register'),
    path('login/', views.LoginView.as_view(), name='login'),
    path('refresh/', TokenRefreshView.as_view(), name='refresh'),
    path('logout/', views.LogoutView.as_view(), name='logout'),
    path('password/change/', views.PasswordChangeView.as_view(), name='password-change'),
    path('password/reset/', views.PasswordResetRequestView.as_view(), name='password-reset'),
    path(
        'password/reset/confirm/',
        views.PasswordResetConfirmView.as_view(),
        name='password-reset-confirm',
    ),
    path('me/', views.MeView.as_view(), name='me'),
    path('profile/', views.ProfileView.as_view(), name='profile'),
    path('profile/classes/', views.TakenClassListView.as_view(), name='class-list'),
    path('profile/classes/<uuid:pk>/', views.TakenClassDetailView.as_view(), name='class-detail'),
    path('profile/certificates/', views.CertificateListView.as_view(), name='certificate-list'),
    path(
        'profile/certificates/<uuid:pk>/',
        views.CertificateDetailView.as_view(),
        name='certificate-detail',
    ),
    path('profile/skills/', views.SkillListView.as_view(), name='skill-list'),
    path('profile/skills/<uuid:pk>/', views.SkillDetailView.as_view(), name='skill-detail'),
]
