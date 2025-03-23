# accounts/views/web.py
# These views are used by the web app for authentication and user management.

from django.contrib.auth import get_user_model, authenticate, login, logout
from django.contrib.auth.tokens import default_token_generator
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.http import HttpResponseNotAllowed
from django.utils.http import urlsafe_base64_decode
from django.views import View

from rest_framework import status
from rest_framework.response import Response

from ..forms import UserRegisterForm, UserLoginForm, PatientRegisterForm


User = get_user_model()


def register(request):
    if request.method == 'POST':
        user = request.user
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
    elif request.method == 'GET':
        user = request.user
        if user.is_authenticated and user.role == 'staff':
            # Staff can register users with any role - staff, doctor, or patient
            form = UserRegisterForm()
        else:
            # Anonymous users can only register as patients - to prevent abuse
            form = PatientRegisterForm()
        return render(request, 'accounts/register.html', {'form': form})
    return HttpResponseNotAllowed(['GET', 'POST'])


def user_login(request):
    user = request.user
    if user.is_authenticated:
        return redirect('home')

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


class PasswordResetRequestView(View):
    template_name = "accounts/password_reset_request.html"

    def get(self, request):
        return render(request, self.template_name, {})


class PasswordResetConfirmView(View):
    template_name = "accounts/password_reset_confirm.html"

    def get(self, request, uidb64, token):
        try:
            uid = urlsafe_base64_decode(uidb64).decode()
            user = User.objects.get(pk=uid)
        except (User.DoesNotExist, ValueError, TypeError):
            return Response({"error": "Invalid reset link."}, status=status.HTTP_400_BAD_REQUEST)

        if not default_token_generator.check_token(user, token):
            return render(request, 'minimal-info.html', {"info": "The password reset link is invalid or has expired. Please request a new one."})

        return render(request, self.template_name, {"uidb64": uidb64, "token": token})


@login_required
def profile(request):
    user = request.user
    context = {
        "user": user,
        "doctor": getattr(user, "doctor", None),
        "patient": getattr(user, "patient", None),
    }
    return render(request, "accounts/profile.html", context)
