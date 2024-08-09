from rest_framework.authtoken import views
from django.urls import path
from .views import RegisterView, LogoutView, login


urlpatterns = [
    path('get-auth/', views.obtain_auth_token, name='get-auth'),
    path('register/', RegisterView.as_view(), name='register'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('login/', login, name='login'),
]
