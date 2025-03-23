from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.home, name='home'),
    path('patients/', views.patient_list, name='patients'),
    path('patients/<str:username>/', views.patient, name='patient'),
    path('sessions/', views.session_list, name='sessions'),
    path('sessions/<str:session_id>/', views.session, name='session'),
    path('assessments/', views.assessment_list, name='assessments'),
    path('assessments/<str:assessment_id>/', views.assessment, name='assessment'),
    path('settings/', views.settings, name='settings'),
    path('toggle-alerts/<str:user_id>/', views.toggle_alerts, name='toggle-alerts'),
    path("assessment-chart/<str:patient_id>/", views.assessment_scores_chart, name="assessment-chart"),
    path("export/", views.export, name="export"),
    path("export/<str:username>/", views.export_patient, name="export-patient"),
]