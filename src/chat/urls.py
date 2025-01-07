from django.urls import path
from . import views


app_name = 'chat'

urlpatterns = [
    path('', views.home, name='home'),
    path('api/chat/', views.chat, name='chat'),

    path('test/', views.test, name='test'),
]
