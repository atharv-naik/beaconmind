from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from .models import Doctor, Patient


User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'phone', 'address', 'is_doctor', 'is_patient', 'password', 'first_name', 'last_name')
        extra_kwargs = {
            'password': {'write_only': True, 'required': True},
            'username': {'required': True},
            'email': {'required': True},
        }

    def create(self, validated_data):
        is_doctor = validated_data.pop('is_doctor', False)
        is_patient = validated_data.pop('is_patient', False)
        user = User.objects.create_user(**validated_data)
        user.is_doctor = is_doctor
        user.is_patient = is_patient
        user.save()

        if is_doctor:
            Doctor.objects.create(user=user)
        elif is_patient:
            Patient.objects.create(user=user)

        Token.objects.create(user=user)
        return user
