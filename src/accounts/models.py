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

class PHQ9Assessment(models.Model):
    id = ShortUUIDField(primary_key=True, prefix='assess_')
    patient = models.OneToOneField(Patient, related_name='phq9_assessment', on_delete=models.CASCADE)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Assessment for {self.patient.user.username}"

class PHQ9Question(models.Model):
    id = ShortUUIDField(primary_key=True, prefix='q_')
    assessment = models.ForeignKey(PHQ9Assessment, related_name='questions', on_delete=models.CASCADE)
    question_id = models.IntegerField() # Question number (1-9)
    question_text = models.CharField(max_length=255, default='')
    score = models.IntegerField()  # Score from 0-3
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Question #{self.question_id} (score: {self.score}) in {self.assessment}"

class PHQ9Score(models.Model):
    id = ShortUUIDField(primary_key=True, prefix='score_')
    assessment = models.ForeignKey(PHQ9Assessment, related_name='scores', on_delete=models.CASCADE)
    score = models.IntegerField()  # Overall score from 0-27
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"PHQ9 Score {self.score} for {self.assessment.patient.user.username} on {self.timestamp.strftime('%b. %d, %Y')}"
