import csv
from django.shortcuts import render, get_object_or_404

from assessments.models import Assessment, AssessmentResult
from assessments.definitions import PhaseMap
from chat.models import ChatSession
from accounts.models import Patient, Doctor
from assessments.definitions import PhaseMap
from django.contrib.auth.decorators import permission_required

from django.utils.timezone import now, timedelta
from django.http import HttpResponse, HttpResponseNotAllowed, JsonResponse
import json

from . import services


@permission_required('accounts.can_access_dashboard', raise_exception=True)
def home(request):
    data = services.get_data_overview()
    return render(request, 'dashboard/home.html', data)


@permission_required('accounts.can_access_dashboard', raise_exception=True)
def assessment_list(request):
    assessments = Assessment.objects.all()
    return render(request, 'dashboard/assessment-list.html', {
        'assessments': assessments, 
        'phase_map': PhaseMap
    })


@permission_required('accounts.can_access_dashboard', raise_exception=True)
def session_list(request):
    sessions = ChatSession.objects.all()
    return render(request, 'dashboard/session-list.html', {
        'sessions': sessions
    })


@permission_required('accounts.can_access_dashboard', raise_exception=True)
def patient_list(request):
    search_query = request.GET.get('q', '').strip().lower()
    sort_order = request.GET.get('sort', 'desc')

    patients = Patient.objects.select_related('user').all()

    if search_query:
        patients = patients.filter(user__username__icontains=search_query)

    if sort_order == 'asc':
        patients = patients.order_by('user__date_joined')
    else:
        patients = patients.order_by('-user__date_joined')

    return render(request, 'dashboard/patient-list.html', {'patients': patients, 'sort': sort_order, 'q': search_query})


@permission_required('accounts.can_access_dashboard', raise_exception=True)
def assessment(request, assessment_id):
    assessment = get_object_or_404(Assessment, id=assessment_id)
    records = assessment.records.all().order_by('question_id')
    result = getattr(assessment, 'result', None)

    scores = []
    phase = PhaseMap.get(assessment.type)
    idx = 0
    curr_score = 0
    n_records = records.count()
    for record in records:
        if idx < n_records and records[idx].question_id == record.question_id:
            scores.append(records[idx].score)
            curr_score += records[idx].score
            idx += 1
        else:
            scores.append(0)

    return render(request, 'dashboard/assessment.html', {
        'assessment': assessment,
        'records': records,
        'scores': scores,
        'curr_score': curr_score,
        'result': result,
        'phase': phase,
    })


@permission_required('accounts.can_access_dashboard', raise_exception=True)
def session(request, session_id):
    session = get_object_or_404(ChatSession, id=session_id)
    return render(request, 'dashboard/session.html', {
        'session': session
    })


@permission_required('accounts.can_access_dashboard', raise_exception=True)
def patient(request, username):
    patient = get_object_or_404(Patient, user__username=username)
    assessments = []
    for a_type in PhaseMap.all():
        assessments.append([
            a_type.verbose_name,
            patient.assessments.filter(type=a_type, status='completed').count(),
        ])
    # 3 month max
    MAX_DAYS = 90
    sessions_obj = patient.user.conversation.chatsession_set.filter(
        status__in=['closed', 'open'],
        timestamp__gte=now() - timedelta(days=MAX_DAYS)
        ).order_by('-timestamp')
    assessments_obj = patient.assessments.filter(
        status='completed', 
        completed_at__gte=now() - timedelta(days=MAX_DAYS)
    ).order_by('-completed_at')

    return render(request, 'dashboard/patient.html', {
        'patient': patient,
        'assessments': assessments,
        'sessions_obj': sessions_obj,
        'assessments_obj': assessments_obj
    })


@permission_required('accounts.can_access_dashboard', raise_exception=True)
def assessment_scores_chart(request, patient_id):
    try:
        patient_assessments = AssessmentResult.objects.filter(
            assessment__patient_id=patient_id
        ).select_related('assessment').order_by('timestamp')
        if not patient_assessments.exists():
            return JsonResponse({"error": "No assessments data."}, status=404)

        data = services.get_assessment_score_chart_data(patient_assessments)
        return JsonResponse(data)
    except Exception as e:
        return JsonResponse({"error": f"An error occurred while fetching data. {e}"}, status=500)



@permission_required('accounts.can_access_dashboard', raise_exception=True)
def settings(request):
    return render(request, 'dashboard/settings.html')


@permission_required('accounts.can_access_dashboard', raise_exception=True)
def toggle_alerts(request, user_id):
    if request.method == 'POST':
        data = json.loads(request.body)
        doctor = get_object_or_404(Doctor, user_id=user_id)
        doctor.receive_patient_alerts = data.get('receive_patient_alerts', False)
        doctor.save(update_fields=['receive_patient_alerts'])
        return JsonResponse({'status': 'success', 'receive_patient_alerts': doctor.receive_patient_alerts})
    return HttpResponseNotAllowed(['POST'])


@permission_required('accounts.can_access_dashboard', raise_exception=True)
def export_patient(request, username):
    patient = get_object_or_404(Patient, user__username=username)
    from_date = request.GET.get('from', None)
    to_date = request.GET.get('to', None)
    response = services.export_patient_pdf(patient, from_date, to_date)
    if not response:
        return HttpResponse("No data available for export.", status=404)
    return response


@permission_required('accounts.can_access_dashboard', raise_exception=True)
def export(request):
    u_name_filter = request.GET.get('filter', None)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="export_{now().strftime("%Y-%m-%d")}.csv"'
    writer = csv.writer(response)
    services.make_export_all(writer, u_name_filter)
    return response
