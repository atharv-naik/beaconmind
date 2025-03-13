from django.db import models
from django.contrib.auth.models import AbstractUser
from shortuuid.django_fields import ShortUUIDField
from assessments.definitions import PhaseMap
from django.core.validators import EmailValidator
from phonenumber_field.modelfields import PhoneNumberField


class User(AbstractUser):
    first_name = models.CharField(max_length=30, default="Anonymous", null=True, blank=True)
    email = models.EmailField("Email Address", validators=[EmailValidator()], unique=True)
    phone = PhoneNumberField(region='IN', blank=True, null=True)
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
    phase = models.CharField(max_length=30, default=PhaseMap.first())

    def __str__(self):
        return self.user.username
