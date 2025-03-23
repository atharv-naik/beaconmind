from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import Doctor, Patient
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType


User = get_user_model()

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        if instance.role == 'doctor':
            Doctor.objects.create(user=instance)
            assign_permissions(permissions=['can_access_dashboard', 'can_view_chat_session'],
            user=instance)
        elif instance.role == 'patient':
            Patient.objects.create(user=instance)
            assign_permissions(permissions=['can_perform_chat'], user=instance)
        elif instance.role == 'staff':
            instance.is_staff = True
        instance.save()

def assign_permissions(permissions, user):
    """Grant permissions to user."""
    for permission in permissions:
        permission = Permission.objects.get(
            codename=permission,
            content_type=ContentType.objects.get_for_model(User)
        )
        user.user_permissions.add(permission)
