from django.urls import path
from . import views


app_name = 'chat'

urlpatterns = [
    path('api/chat/', views.chat, name='chat'),
    path('', views.home, name='home'),
]
