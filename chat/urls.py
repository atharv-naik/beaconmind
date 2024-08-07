from django.urls import path
from . import views


urlpatterns = [
    path('chat/', views.chat),
    path('chat/delete/', views.delete_conversation),
    path('chat/get-titles/', views.get_title),
    path('chat/get-data/', views.get_data)
]
