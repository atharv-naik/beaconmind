from django.db import models
from django.contrib.auth.models import AbstractUser
from shortuuid.django_fields import ShortUUIDField


class User(AbstractUser):
    phone = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    ROLE_CHOICES = (
        ('doctor', 'Doctor'),
        ('patient', 'Patient'),
        ('staff', 'Staff'),
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default='staff')

class Doctor(models.Model):
    id = ShortUUIDField(primary_key=True, prefix='doc_')
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    department = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.user.username

class Patient(models.Model):
    id = ShortUUIDField(primary_key=True, prefix='pat_')
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.user.username

class Assessment(models.Model):
    id = ShortUUIDField(primary_key=True, prefix='assess_')
    patient = models.ForeignKey(Patient, related_name='assessment', on_delete=models.CASCADE)
    types = (
        ('phq9', 'PHQ9'),
        # ('gad7', 'GAD7'), # TODO: Add GAD7
    )
    type = models.CharField(max_length=10, choices=types, default='phq9')
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Assessment for {self.patient.user.username}"

class AssessmentRecord(models.Model):
    id = ShortUUIDField(primary_key=True, prefix='q_')
    assessment = models.ForeignKey(Assessment, related_name='questions', on_delete=models.CASCADE)
    question_id = models.IntegerField()
    question_text = models.CharField(max_length=255, default='')
    score = models.IntegerField()
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Question #{self.question_id} (score: {self.score}) in {self.assessment}"

class AssessmentResult(models.Model):
    id = ShortUUIDField(primary_key=True, prefix='score_')
    assessment = models.ForeignKey(Assessment, related_name='scores', on_delete=models.CASCADE)
    score = models.IntegerField()
    severities = (
        ('minimal', 'Minimal'),
        ('mild', 'Mild'),
        ('moderate', 'Moderate'),
        ('moderately-severe', 'Moderately Severe'),
        ('severe', 'Severe'),
    )
    severity = models.CharField(max_length=20, choices=severities, default='minimal')
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"PHQ9 Score {self.score} for {self.assessment.patient.user.username} on {self.timestamp.strftime('%b. %d, %Y')}"
