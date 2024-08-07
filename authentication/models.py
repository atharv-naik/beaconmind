from django.db import models
from django.contrib.auth.models import AbstractUser
from shortuuid.django_fields import ShortUUIDField


class User(AbstractUser):
    phone = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    is_doctor = models.BooleanField(default=False)
    is_patient = models.BooleanField(default=False)

class Doctor(models.Model):
    id = ShortUUIDField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    department = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return self.user.username

class Patient(models.Model):
    id = ShortUUIDField(primary_key=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.user.username
