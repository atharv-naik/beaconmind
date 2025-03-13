from django.urls import path
from . import views


app_name = 'accounts'

api_urlpatterns = [
    path('api/get-auth/', views.api.LoginView.as_view(), name='api-get-auth'),
    path('api/register/', views.api.RegisterView.as_view(), name='api-register'),
    path('api/logout/', views.api.LogoutView.as_view(), name='api-logout'),
    path('api/profile/', views.api.ProfileView.as_view(), name='api-profile'),
    path('api/password-reset/', views.api.PasswordResetView.as_view(), name='api-password-reset'),
    path('api/password-reset/request/', views.api.PasswordResetRequestView.as_view(), name='api-password-reset-request'),
    path('api/password-reset/confirm/<uidb64>/<token>/', views.api.PasswordResetConfirmView.as_view(), name='api-password-reset-confirm'),
] # urls for auth api used from mobile app

urlpatterns = [
    path('login/', views.web.user_login, name='login'),
    path('logout/', views.web.user_logout, name='logout'),
    path('register/', views.web.register, name='register'),
    path('password-reset/request/', views.web.PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('password-reset/confirm/<uidb64>/<token>/', views.web.PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
] + api_urlpatterns
