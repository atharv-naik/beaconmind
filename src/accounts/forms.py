from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User


class UserRegisterForm(UserCreationForm):
    phone = forms.CharField(required=False)
    address = forms.CharField(widget=forms.Textarea, required=False)
    email = forms.EmailField(required=True)
    choices = User.ROLE_CHOICES
    role = forms.ChoiceField(choices=choices, required=False, initial='staff', widget=forms.Select(attrs={'class': 'form-control'}), label='Register as')
    
    class Meta:
        model = User
        fields = ['username', 'email', 'phone', 'address', 'password1', 'password2', 'role']


class UserRegisterFormStrict(UserRegisterForm):
    choices = [('patient', 'Patient')]
    role = forms.ChoiceField(choices=choices, required=True, widget=forms.Select(attrs={'class': 'form-control'}), label='Register as')

class UserLoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Username'}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': 'Password'}))
