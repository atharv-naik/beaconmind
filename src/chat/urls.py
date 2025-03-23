from django.urls import path
from . import views


app_name = 'chat'

urlpatterns = [
    path('', views.home, name='home'),
    path('session/<str:session_id>/', views.session_page, name='session-page'),
    path('api/chat/', views.chat, name='chat'),
    path('api/session/<str:session_id>/', views.session, name='api-session'),
]
