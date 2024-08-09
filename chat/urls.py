from django.urls import path
from . import views


urlpatterns = [
    path('chat/', views.chat, name='chat'),
    path('', views.signin, name='signin'),
    path('chatbot/', views.chatbot, name='chatbot'),
]
