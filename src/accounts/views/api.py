# accounts/views/api.py
# These views are used by the mobile app for authentication and user management.

from django.contrib.auth import get_user_model
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.conf import settings
from django.utils import timezone
from django.http import JsonResponse

from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token

from ..serializers import (
    PasswordResetSerializer,
    PasswordResetRequestSerializer,
    UserRegisterSerializer,
    UserSerializer
)
import json


User = get_user_model()


class RegisterView(generics.CreateAPIView):
    serializer_class = UserRegisterSerializer # role restrictions are enforced on the frontend
    queryset = User.objects.all()

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        user = User.objects.get(username=response.data['username'])
        token = Token.objects.get(user=user)
        response.data['token'] = token.key
        return response


class LoginView(ObtainAuthToken):
    """
    Extends ObtainAuthToken class to update last_login field on successful token based login
    """

    def post(self, request, *args, **kwargs):
        try:
            response = super().post(request, *args, **kwargs)
            user = self.serializer_class(data=request.data)
            user.is_valid(raise_exception=True)
            user = user.validated_data['user']
            
            user.last_login = timezone.now()
            user.save(update_fields=['last_login'])

            return response
        except Exception as e:
            return Response({'detail': f'Invalid credentials. {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)


class LogoutView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            request._user.auth_token.delete()
            return Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)
        except AttributeError:
            return Response({"detail": "Invalid request. No token found."}, status=status.HTTP_400_BAD_REQUEST)


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def put(self, request):
        serializer = UserSerializer(request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PasswordResetView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def post(self, request):
        serializer = PasswordResetSerializer(
            data=request.data, context={'request': request})
        if serializer.is_valid():
            request.user.set_password(
                serializer._validated_data['new_password'])
            request.user.save()
            return Response({'detail': 'Password changed successfully.'}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def send_password_reset_email(user, reset_link):
    send_mail_subject = 'Password Reset Request'
    plain_message = f'Click the following link to reset your password: {reset_link}'
    html_message = render_to_string('accounts/emails/password_reset_email.html', {
        'reset_link': reset_link,
        'current_year': timezone.now().year
    })

    email = EmailMultiAlternatives(
        subject=send_mail_subject,
        body=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[user.email]
    )
    email.attach_alternative(html_message, "text/html")
    email.send(fail_silently=False)


class PasswordResetRequestView(APIView):
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        if serializer.is_valid():
            user = get_object_or_404(User, email=serializer.validated_data['email'])
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            reset_link = request.build_absolute_uri(
                reverse('accounts:password-reset-confirm', kwargs={'uidb64': uid, 'token': token}))
            send_password_reset_email(user, reset_link)
            return Response({'detail': 'Password reset link sent to your email.'}, status=status.HTTP_200_OK)
        error_text = str(serializer.errors['email'][0])
        return Response({'error': error_text}, status=status.HTTP_400_BAD_REQUEST)

class PasswordResetConfirmView(APIView):
    def post(self, request, uidb64, token):
        if request.user.is_authenticated:
            return JsonResponse({"error": "You are already logged in."}, status=400)
        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
        except (User.DoesNotExist, ValueError, TypeError):
            return JsonResponse({"error": "Invalid reset link."}, status=400)

        if not default_token_generator.check_token(user, token):
            return JsonResponse({"error": "Reset link has expired or is invalid."}, status=400)

        data = json.loads(request.body)
        new_password1 = data.get("new_password1")
        new_password2 = data.get("new_password2")

        if not new_password1 or not new_password2:
            return JsonResponse({"error": "Both fields are required."}, status=400)

        if new_password1 != new_password2:
            return JsonResponse({"error": "Passwords do not match."}, status=400)

        Token.objects.filter(user=user).delete
        user.set_password(new_password1)
        user.save()

        return JsonResponse({"detail": "Password reset successfully."}, status=200)
