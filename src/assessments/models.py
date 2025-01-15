from django.db import models
from shortuuid.django_fields import ShortUUIDField

from accounts.models import Patient
from assessments.definitions import PHQ9Phase


class Assessment(models.Model):
    types = (
        (PHQ9Phase().name, PHQ9Phase().verbose_name),
        # ('gad7', 'GAD7'), # TODO: Add GAD7
    )
    status = (
        ('pending', 'Pending'),
        ('completed', 'Completed'),
    )
    id = ShortUUIDField(primary_key=True, prefix='assess_')
    patient = models.ForeignKey(Patient, related_name='assessments', on_delete=models.CASCADE)
    type = models.CharField(max_length=30, choices=types, default=PHQ9Phase().name)
    status = models.CharField(max_length=10, choices=status, default='pending')
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.patient.user.username}'s {self.get_type_display()} assessment"

class AssessmentRecord(models.Model):
    id = ShortUUIDField(primary_key=True, prefix='rec_')
    assessment = models.ForeignKey(Assessment, related_name='records', on_delete=models.CASCADE)
    question_id = models.IntegerField()
    question_text = models.CharField(max_length=255, default='')
    score = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)
    remarks = models.TextField(blank=True, null=True)

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
