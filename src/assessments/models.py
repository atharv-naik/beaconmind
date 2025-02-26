from django.db import models
from shortuuid.django_fields import ShortUUIDField

from accounts.models import Patient
from chat.models import ChatSession
from assessments.definitions import PHQ9Phase, GAD7Phase, MonitoringPhase, ASQPhase


class Assessment(models.Model):
    _types = (
        (PHQ9Phase().name, PHQ9Phase().verbose_name),
        (GAD7Phase().name, GAD7Phase().verbose_name),
        (MonitoringPhase().name, MonitoringPhase().verbose_name),
        (ASQPhase().name, ASQPhase().verbose_name),
    )
    _status = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
        ('aborted', 'Aborted'),
    )
    id = ShortUUIDField(primary_key=True, prefix='assess_')
    patient = models.ForeignKey(Patient, related_name='assessments', on_delete=models.CASCADE)
    session = models.ForeignKey(ChatSession, related_name='assessments', on_delete=models.CASCADE, null=True, blank=True)
    type = models.CharField(max_length=30, choices=_types, default=PHQ9Phase().name)
    status = models.CharField(max_length=10, choices=_status, default='pending')
    timestamp = models.DateTimeField(verbose_name="Started at", auto_now_add=True)
    completed_at = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.patient.user.username}'s {self.get_type_display()} assessment"

class AssessmentRecord(models.Model):
    id = ShortUUIDField(primary_key=True, prefix='rec_')
    assessment = models.ForeignKey(Assessment, related_name='records', on_delete=models.CASCADE)
    question_id = models.IntegerField()
    question_text = models.CharField(max_length=255, default='')
    score = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)
    remark = models.TextField(blank=True, null=True)
    snippet = models.TextField(blank=True, null=True)
    keywords = models.JSONField(blank=True, null=True, default=list)
    dirty = models.BooleanField(default=False)

    class Meta:
        verbose_name = 'Assessment Record'
        verbose_name_plural = 'Assessment Records'

    def __str__(self):
        return f"[Q{self.question_id} : {self.score}] in {self.assessment}"

class AssessmentResult(models.Model):
    id = ShortUUIDField(primary_key=True, prefix='res_')
    assessment = models.OneToOneField(Assessment, related_name='result', on_delete=models.CASCADE)
    score = models.IntegerField()
    severity = models.CharField(max_length=20, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Assessment Result'
        verbose_name_plural = 'Assessment Results'

    def __str__(self):
        return f"{self.assessment.patient.user.username}'s {self.assessment.get_type_display()} assessment result"
