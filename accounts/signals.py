from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Doctor, Patient


User = get_user_model()

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        if instance.role == 'doctor':
            Doctor.objects.create(user=instance)
        elif instance.role == 'patient':
            Patient.objects.create(user=instance)

@receiver(pre_save, sender=User)
def update_user_profile(sender, instance, **kwargs):
    if instance.pk:
        try:
            old_instance = User.objects.get(pk=instance.pk)
        except User.DoesNotExist:
            return
        if instance.role != old_instance.role: # role is updated
            if instance.role == 'doctor':
                Doctor.objects.create(user=instance)
                Patient.objects.filter(user=instance).delete()
            elif instance.role == 'patient':
                Patient.objects.create(user=instance)
                Doctor.objects.filter(user=instance).delete()
            else:
                Doctor.objects.filter(user=instance).delete()
                Patient.objects.filter(user=instance).delete()
