from rest_framework.authtoken.views import ObtainAuthToken
from django.urls import path
from . import views


app_name = 'accounts'

api_urlpatterns = [
    path('api/get-auth/', ObtainAuthToken.as_view(), name='api-get-auth'),
    path('api/register/', views.RegisterView.as_view(), name='api-register'),
    path('api/logout/', views.LogoutView.as_view(), name='api-logout'),
] # urls for auth api used from mobile app

urlpatterns = [
    path('login/', views.user_login, name='login'),
    path('register/', views.register, name='register'),
] + api_urlpatterns
