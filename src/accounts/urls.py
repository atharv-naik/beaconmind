from django.urls import path
from . import views


app_name = 'accounts'

api_urlpatterns = [
    path('api/get-auth/', views.LoginView.as_view(), name='api-get-auth'),
    path('api/register/', views.RegisterView.as_view(), name='api-register'),
    path('api/logout/', views.LogoutView.as_view(), name='api-logout'),
    path('api/password-reset/', views.PasswordResetView.as_view(), name='api-password-reset'),
] # urls for auth api used from mobile app

urlpatterns = [
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('register/', views.register, name='register'),
] + api_urlpatterns
