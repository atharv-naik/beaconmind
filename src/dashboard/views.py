from django.shortcuts import render, get_object_or_404

from assessments.models import Assessment
from assessments.definitions import PhaseMap
from accounts.decorators import allow_only


@allow_only(['doctor'])
def home(request):
    assessments = Assessment.objects.all()
    return render(request, 'dashboard/home.html', {'assessments': assessments})


@allow_only(['doctor'])
def assessment(request, assessment_id):
    assessment = get_object_or_404(Assessment, id=assessment_id)
    records = assessment.records.all().order_by('question_id')
    result = getattr(assessment, 'result', None)

    scores = []
    phase = PhaseMap.get(assessment.type)
    idx = 0
    curr_score = 0
    for q_id in range(1, phase.N + 1):
        if idx < records.count() and records[idx].question_id == q_id:
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
