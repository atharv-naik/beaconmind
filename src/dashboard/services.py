from collections import defaultdict
from datetime import datetime, timedelta
from accounts.models import Patient, Doctor
from assessments.models import Assessment, AssessmentResult
from chat.models import ChatSession
from django.db.models import Avg
from assessments.definitions import PhaseMap
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils.timezone import now
from weasyprint import HTML


def get_data_overview():
    """
    Returns an overview of the data for the dashboard.
    """

    total_patients = Patient.objects.count()
    total_doctors = Doctor.objects.count()
    
    total_sessions = ChatSession.objects.count()
    one_week_ago = now() - timedelta(days=7)
    sessions_last_week = ChatSession.objects.filter(timestamp__gte=one_week_ago).count()
    
    assessment_types = PhaseMap.all()

    assessment_type_codes = Assessment.objects.values_list('type', flat=True).distinct()

    assessments_completed_all_time = {}
    assessments_completed_last_week = {}
    avg_assessment_score_all_time = {}
    avg_assessment_score_last_week = {}

    for a_type in assessment_type_codes:
        assessments_completed_all_time[a_type] = Assessment.objects.filter(
            type=a_type, status='completed'
        ).count()

        assessments_completed_last_week[a_type] = Assessment.objects.filter(
            type=a_type, status='completed', completed_at__gte=one_week_ago
        ).count()

        avg_all_time = (
            AssessmentResult.objects.filter(assessment__type=a_type)
            .aggregate(avg_score=Avg('score'))['avg_score'] or 0
        )
        avg_last_week = (
            AssessmentResult.objects.filter(assessment__type=a_type, assessment__completed_at__gte=one_week_ago)
            .aggregate(avg_score=Avg('score'))['avg_score'] or 0
        )

        avg_assessment_score_all_time[a_type] = round(avg_all_time, 1)
        avg_assessment_score_last_week[a_type] = round(avg_last_week, 1)
    
    assessment_stats = {}
    for a_type in assessment_type_codes:
        total_count = Assessment.objects.filter(type=a_type, status='completed').count()
        last_week_count = Assessment.objects.filter(type=a_type, status='completed', completed_at__gte=one_week_ago).count()
        
        avg_score_all_time = AssessmentResult.objects.filter(assessment__type=a_type).aggregate(avg_score=Avg('score'))['avg_score'] or 0
        avg_score_last_week = AssessmentResult.objects.filter(assessment__type=a_type, assessment__completed_at__gte=one_week_ago).aggregate(avg_score=Avg('score'))['avg_score'] or 0

        assessment_stats[a_type] = {
            "total_count": total_count,
            "last_week_count": last_week_count,
            "avg_score_all_time": round(avg_score_all_time, 1),
            "avg_score_last_week": round(avg_score_last_week, 1)
        }
    
    completed_sessions_all_time = ChatSession.objects.filter(status='closed').count()
    completed_sessions_last_week = ChatSession.objects.filter(status='closed', timestamp__gte=one_week_ago).count()

    data = {
        'total_patients': total_patients,
        'total_doctors': total_doctors,
        'total_sessions': total_sessions,
        'sessions_last_week': sessions_last_week,
        'assessment_types': assessment_types,
        'assessments_completed_all_time': assessments_completed_all_time,
        'assessments_completed_last_week': assessments_completed_last_week,
        'avg_assessment_score_all_time': avg_assessment_score_all_time,
        'avg_assessment_score_last_week': avg_assessment_score_last_week,
        'completed_sessions_all_time': completed_sessions_all_time,
        'completed_sessions_last_week': completed_sessions_last_week,
        'assessment_stats': assessment_stats  
    }

    return data


def get_assessment_score_chart_data(patient_assessments):
        data = defaultdict(list)

        # Organizing data by assessment type
        for result in patient_assessments:
            assessment_type = result.assessment.type
            data[assessment_type].append({
                "date": result.timestamp.strftime("%d %b"),  # Format date for Chart.js
                "score": result.score
            })
        
        last_assessment_date = patient_assessments.last().timestamp.date()

        # Get patient's joining date
        patient_joining_date = result.assessment.patient.user.date_joined.date()

        # Ensure continuous dates even if assessments are sparse
        date_range = [patient_joining_date + timedelta(days=i) for i in range((
            last_assessment_date - patient_joining_date).days + 1
            )]
        
        formatted_data = {}
        for assessment_type, entries in data.items():
            scores_by_date = {entry["date"]: entry["score"] for entry in entries}

            formatted_data[assessment_type] = [
                scores_by_date.get(date.strftime("%d %b"), None)
                for date in date_range
            ]

        data = {
            "labels": [date.strftime("%d %b") for date in date_range],
            "datasets": [
                {"label": "PHQ9", "data": formatted_data.get("assessment.phq9", [])},
                {"label": "GAD7", "data": formatted_data.get("assessment.gad7", [])},
                {"label": "ASQ", "data": formatted_data.get("assessment.asq", [])},
            ],
            "from_date": patient_joining_date,
            "to_date": last_assessment_date,
        }

        return data


def make_export_all(writer, u_name_filter=None):
    """
    Exports patient assessment data to a CSV file.
    
    The export includes user details, session details, responses to assessments (PHQ-9, GAD-7, ASQ, etc.), and scores.
    
    Example CSV output format:
    
    | Username | Email       | Phone     | Session Date | Session ID | Session Status | PHQ-9 Q1 | ... | PHQ-9 Score | GAD-7 Q1 | ... | GAD-7 Score |
    |----------|-------------|-----------|--------------|------------|----------------|----------|-----|-------------|----------|-----|-------------|
    | user1    | user1@mail  | 123456789 | 2025-03-22   | 1          | completed      | 3        | ... | 15          | 2        | ... | 10          |
    | user2    | user2@mail  | 987654321 | 2025-03-21   | 2          | open           | -        | ... | -           | -        | ... | -           |
    
    """

    NULL_PLACEHOLDER = ''
    
    # excluding test users
    patients = Patient.objects.exclude(user__username__startswith='test.')

    if u_name_filter:
        patients = patients.filter(user__username__icontains=u_name_filter)

    phases = PhaseMap.all()
    
    header = ["Username", "Email", "Phone", "Session Date", "Session ID", "Session Status"]
    
    for phase in phases:
        header.extend([
            f"{phase.verbose_name} Q.{q['qid']} - [{q['text']}]"
            for q in phase.get_questions_dict().values()
        ])
    
    header.extend([
        f"{phase.verbose_name} Score" for phase in phases if phase.supports_scoring
    ])
    
    writer.writerow(header)
    
    for patient in patients:
        user = patient.user

        conversation = getattr(user, 'conversation', None)
        if not conversation:
            continue
        
        sessions = conversation.chatsession_set.all().order_by('timestamp')
        if not sessions.exists():
            continue
        
        for session in sessions:
            row = [
                user.username, user.email, user.phone,
                session.timestamp.strftime('%Y-%m-%d'), session.id, session.status
            ]

            for phase in phases:
                assessment = patient.assessments.filter(type=phase.name, session=session).first()
                if assessment:
                    for qid in phase.get_qids():
                        record = assessment.records.filter(question_id=qid).first()
                        if record:
                            row.append(record.score if phase.supports_scoring else record.remark)
                        else:
                            row.append(NULL_PLACEHOLDER)
                else:
                    row.extend([NULL_PLACEHOLDER] * phase.N)
            
            for phase in phases:
                assessment = patient.assessments.filter(
                    type=phase.name, session=session, status='completed'
                ).select_related('result').first()
                
                row.append(assessment.result.score if (assessment and phase.supports_scoring) else NULL_PLACEHOLDER)
            
            writer.writerow(row)


def export_patient_pdf(patient, from_date=None, to_date=None):
    """
    Exports patient assessment data to a PDF file.
    - If no dates are provided, defaults to the last 3 months.
    - If only from_date is provided, fetches from that date to present.
    - If only to_date is provided, fetches from patient joining date to that date.
    - If both dates are provided, fetches sessions within that range.
    """
    conversation = getattr(patient.user, 'conversation', None)
    if not conversation:
        return None

    try:
        if from_date and isinstance(from_date, str):
            from_date = datetime.strptime(from_date, '%Y-%m-%d').date()
        if to_date and isinstance(to_date, str):
            to_date = datetime.strptime(to_date, '%Y-%m-%d').date()
    except ValueError:
        raise ValueError("Invalid date format. Use 'YYYY-MM-DD'.")

    now_time = now().date()
    joining_date = patient.user.date_joined.date()

    # If no dates provided, default to last 3 months or since patient joined
    if not from_date and not to_date:
        from_date = now_time - timedelta(days=90) if now_time - joining_date > timedelta(days=90) else joining_date
        to_date = now_time

    # If only from_date is provided, set to_date to now
    elif from_date and not to_date:
        to_date = now_time

    # If only to_date is provided, fetch till patient joined
    elif to_date and not from_date:
        from_date = patient.user.date_joined.date()

    sessions = conversation.chatsession_set.filter(
        timestamp__date__gte=from_date,
        timestamp__date__lte=to_date
    ).order_by('-timestamp')

    if not sessions.exists():
        return None
    
    scored_phases = PhaseMap.all()
    
    pdf_pages = []
    
    # First page: patient info
    patient_info_html = render_to_string('dashboard/exports/patient_report_info_page.html', {
        'patient': patient,
        'sessions': sessions,
        'date_range': [from_date, to_date],
    })
    pdf_pages.append(f'<div style="page-break-after: always;">{patient_info_html}</div>')
    
    for phase in scored_phases:
        assessments = patient.assessments.filter(type=phase.name, status='completed', session__in=sessions)

        for assessment in assessments:
            records = assessment.records.all()
            html_content = render_to_string('dashboard/exports/patient_report_assessments_page.html', {
                'patient': patient,
                'phase': phase,
                'records': records,
                'assessment_date': assessment.session.timestamp.strftime('%d %b %Y'),
                'session_id': assessment.session.id,
                'score': assessment.result.score if getattr(assessment, 'result', None) else '-',
            })
            pdf_pages.append(f'<div style="page-break-after: always;">{html_content}</div>')
    
    combined_html = "".join(pdf_pages)
    pdf = HTML(string=combined_html).write_pdf()
    
    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="{patient.user.username}_assessment.pdf"'
    return response
