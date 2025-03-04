from rest_framework import generics
from django.contrib.auth import get_user_model, authenticate, logout
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import TokenAuthentication
from rest_framework.decorators import api_view
from django.shortcuts import render, redirect
from django.contrib.auth import login, authenticate
from .forms import UserRegisterForm, UserLoginForm, PatientRegisterForm
from .serializers import PasswordResetSerializer, UserRegisterSerializer
from django.http import HttpResponseNotAllowed
from rest_framework.authtoken.views import ObtainAuthToken
from django.utils import timezone

User = get_user_model()


class RegisterView(generics.CreateAPIView):
    serializer_class = UserRegisterSerializer # role restrictions are enforced on the frontend
    queryset = User.objects.all()


class LogoutView(APIView):
    authentication_classes = [TokenAuthentication]
    permission_classes = [IsAuthenticated]

    def post(self, request):
        try:
            request._user.auth_token.delete()
            return Response({"detail": "Successfully logged out."}, status=status.HTTP_200_OK)
        except AttributeError:
            return Response({"detail": "Invalid request. No token found."}, status=status.HTTP_400_BAD_REQUEST)


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
            return Response({'detail': f'{e.detail['non_field_errors'][0]}'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'POST'])
def register(request):
    if request.method == 'POST':
        user = request._user
        if user.is_authenticated and user.role == 'staff':
            form = UserRegisterForm(request.POST)
        else:
            form = PatientRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
        else:
            return render(request, 'accounts/register.html', {'form': form})
    else:
        user = request._user
        if user.is_authenticated and user.role == 'staff':
            # Staff can register users with any role - staff, doctor, or patient
            form = UserRegisterForm()
        else:
            # Anonymous users can only register as patients - to prevent abuse
            form = PatientRegisterForm()
        return render(request, 'accounts/register.html', {'form': form})


def user_login(request):
    if request.method == 'POST':
        form = UserLoginForm(data=request.POST)
        login_failed = False
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('home')
            else:
                login_failed = True
        elif form.errors or login_failed:
            return render(request, 'accounts/login.html', {'form': form})
    elif request.method == 'GET':
        form = UserLoginForm()
        return render(request, 'accounts/login.html', {'form': form})
    return HttpResponseNotAllowed(['GET', 'POST'])


def user_logout(request):
    if request.method == 'POST':
        logout(request)
        return redirect('accounts:login')
    return HttpResponseNotAllowed(['POST'])


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
