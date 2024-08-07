from rest_framework.authtoken import views
from django.urls import path
from .views import RegisterView


urlpatterns = [
    path('get-auth/', views.obtain_auth_token),
    path('register/', RegisterView.as_view()),
]
