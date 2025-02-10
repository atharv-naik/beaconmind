from rest_framework import serializers
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from django.contrib.auth.password_validation import validate_password


User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'phone', 'address', 'role', 'password')
        extra_kwargs = {
            'password': {'write_only': True, 'required': True},
            'username': {'required': True},
            'email': {'required': True},
        }

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        Token.objects.create(user=user)
        return user


class UserRegisterSerializer(serializers.ModelSerializer):
    phone = serializers.CharField(required=False, allow_blank=True)
    address = serializers.CharField(required=False, allow_blank=True)
    email = serializers.EmailField(required=True)
    username = serializers.CharField(required=True)
    password1 = serializers.CharField(write_only=True, required=True)
    password2 = serializers.CharField(write_only=True, required=True)
    role = serializers.ChoiceField(choices=User.ROLE_CHOICES, initial='patient', required=True) # role restrictions are enforced on the frontend

    def validate(self, data):
        if data['password1'] != data['password2']:
            raise serializers.ValidationError("Passwords must match.")
        return data

    class Meta:
        model = User
        fields = ['username', 'email', 'phone', 'address', 'password1', 'password2', 'role']
    
    def create(self, validated_data):
        user_data = {key: validated_data[key] for key in validated_data if key != 'password1' and key != 'password2'}
        user = User.objects.create_user(**user_data, password=validated_data['password1'])
        return user

class PasswordResetSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, validators=[validate_password])

    def validate(self, data):
        user = self.context['request'].user
        if not user.check_password(data['old_password']):
            raise serializers.ValidationError("Old password is incorrect.")
        return data
