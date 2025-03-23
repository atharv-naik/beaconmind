from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from unittest.mock import patch
from django.test import TestCase
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils.encoding import force_bytes
from django.contrib.auth.tokens import default_token_generator
from rest_framework import status
from rest_framework.authtoken.models import Token
from .models import Patient, Doctor
from faker import Faker

User = get_user_model()

class AccountsAPITestCase(APITestCase):
    
    def setUp(self):
        """Set up test users."""
        self.client = APIClient()
        self.register_url = reverse('accounts:api-register')
        self.login_url = reverse('accounts:api-get-auth')
        self.logout_url = reverse('accounts:api-logout')
        self.change_password_url = reverse('accounts:api-change-password')
        self.faker = Faker()

        self.staff_user = User.objects.create_user(
            username='staffuser',
            email=self.faker.email(),
            password='staffpass',
            role='staff'
        )
        self.doctor_user = User.objects.create_user(
            username='doctoruser', 
            email=self.faker.email(),
            password='doctorpass', 
            role='doctor'
        )
        self.patient_user = User.objects.create_user(
            username='patientuser',
            email=self.faker.email(),
            password='patientpass',
            role='patient'
        )
        self.staff_token = Token.objects.create(user=self.staff_user)
        self.doctor_token = Token.objects.create(user=self.doctor_user)
        self.patient_token = Token.objects.create(user=self.patient_user)
    
    def test_register_and_login_new_patient(self):
        data = {
            'username': 'newpatient',
            'email': self.faker.email(),
            'password1': 'strongpass123',
            'password2': 'strongpass123',
            'role': 'patient'
        }
        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('token', response.data)
        self.assertTrue(User.objects.filter(username='newpatient').exists())

        data = {'username': 'newpatient', 'password': 'strongpass123'}
        response = self.client.post(self.login_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        self.assertTrue(Token.objects.filter(user=User.objects.get(username='newpatient')).exists())
    
    def test_valid_roles_created_after_register(self):
        data = {
            'username': 'newstaff',
            'email': self.faker.email(),
            'password1': 'strongpass123',
            'password2': 'strongpass123',
            'phone': '1234567890',
            'address': '123 Test St',
            'role': 'staff'
        }
        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username='newstaff').exists())
        self.assertEqual(User.objects.get(username='newstaff').role, 'staff')

        data.update({'username': 'newdoctor', 'role': 'doctor', 'email': self.faker.email()})
        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username='newdoctor').exists())
        self.assertEqual(User.objects.get(username='newdoctor').role, 'doctor')
        self.assertTrue(Doctor.objects.filter(user=User.objects.get(username='newdoctor')).exists())
        self.assertFalse(Patient.objects.filter(user=User.objects.get(username='newdoctor')).exists())

        data.update({'username': 'newpatient', 'role': 'patient', 'email': self.faker.email()})
        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username='newpatient').exists())
        self.assertEqual(User.objects.get(username='newpatient').role, 'patient')
        self.assertTrue(Patient.objects.filter(user=User.objects.get(username='newpatient')).exists())
        self.assertFalse(Doctor.objects.filter(user=User.objects.get(username='newpatient')).exists())

    
    def test_login_valid_user(self):
        data = {'username': 'staffuser', 'password': 'staffpass'}
        response = self.client.post(self.login_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
        self.staff_token = response.data['token']

        data = {'username': 'doctoruser', 'password': 'doctorpass'}
        response = self.client.post(self.login_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)

        data = {'username': 'patientuser', 'password': 'patientpass'}
        response = self.client.post(self.login_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
    
    def test_login_wrong_password(self):
        data = {'username': 'staffuser', 'password': 'wrongpass'}
        response = self.client.post(self.login_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_username_does_not_exist(self):
        data = {'username': 'wronguser', 'password': 'staffpass'}
        response = self.client.post(self.login_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_login_blank_password(self):
        data = {'username': 'staffuser', 'password': ''}
        response = self.client.post(self.login_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
    
    def test_logout_authenticated_user(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.staff_token}')
        response = self.client.post(self.logout_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(Token.objects.filter(user=self.staff_user).exists())
    
    def test_logout_unauthenticated_user(self):
        response = self.client.post(self.logout_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
    
    def test_change_password(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.staff_token}')
        data = {'old_password': 'staffpass', 'new_password': 'newstrongpass'}
        response = self.client.post(self.change_password_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.staff_user.refresh_from_db()
        self.assertTrue(self.staff_user.check_password('newstrongpass'))
    
    def test_get_user_profile(self):
        data = {
            'username': 'test',
            'email': self.faker.email(),
            'password1': 'strongpass123',
            'password2': 'strongpass123',
            'role': 'patient',
            'phone': '1234567890',
            'address': '123 Test St',
        }

        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self.client.post(self.login_url, {'username': 'test', 'password': 'strongpass123'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {response.data["token"]}')
        response = self.client.get(reverse('accounts:api-profile'))
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        user = User.objects.get(username='test')
        self.assertEqual(data['username'], user.username)
        self.assertEqual(data['email'], user.email)
        self.assertEqual(data['phone'], str(user.phone.national_number))
        self.assertEqual(data['address'], user.address)
        self.assertEqual(data['role'], user.role)

        
    def test_update_user_profile(self):
        data = {
            'username': 'test',
            'email': 'email_before_edit@test.com',
            'password1': 'strongpass123',
            'password2': 'strongpass123',
            'role': 'patient',
            'phone': '1234567890',
            'address': '123 Test St',
        }

        response = self.client.post(self.register_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        response = self.client.post(self.login_url, {'username': 'test', 'password': 'strongpass123'}, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        self.client.credentials(HTTP_AUTHORIZATION=f'Token {response.data["token"]}')

        data.update({
            'email': 'updated@test.com',
            'phone': '9876543210',
            'address': '987 Test St',
        })

        response = self.client.put(reverse('accounts:api-profile'), data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        user = User.objects.get(username='test')
        self.assertEqual(user.email, data['email'])
        self.assertEqual(str(user.phone.national_number), data['phone'])
        self.assertEqual(user.address, data['address'])


class PasswordResetTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(email="testuser@example.com", password="OldPassword123", username="testuser")
        self.password_reset_url = reverse("accounts:api-password-reset-request")

    @patch("django.core.mail.EmailMultiAlternatives.send")
    def test_password_reset_request_valid_email(self, mock_send):
        """Test password reset request with a valid email. Ensure email is not actually sent."""
        response = self.client.post(self.password_reset_url, {"email": self.user.email})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("Password reset link sent", response.data["detail"])

        # Ensure email sending function was called, but email is NOT sent
        mock_send.assert_called_once()

    @patch("django.core.mail.EmailMultiAlternatives.send")
    def test_password_reset_request_invalid_email(self, mock_send):
        """Test password reset request with an invalid email."""
        response = self.client.post(self.password_reset_url, {"email": "doesnotexist@example.com"})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("error", response.data)

        # Ensure email was NOT sent
        mock_send.assert_not_called()

    def test_password_reset_confirm_invalid_user(self):
        """Test password reset with an invalid user ID."""
        uidb64 = urlsafe_base64_encode(force_bytes(9999))  # Non-existent user
        token = default_token_generator.make_token(self.user)

        response = self.client.post(reverse("accounts:api-password-reset-confirm", kwargs={"uidb64": uidb64, "token": token}), {})
        self.assertEqual(response.status_code, 400)
        self.assertIn("Invalid reset link", response.json()["error"])

    def test_password_reset_confirm_invalid_token(self):
        """Test password reset with an invalid token."""
        uidb64 = urlsafe_base64_encode(force_bytes(self.user.pk))
        invalid_token = "invalid-token"

        response = self.client.post(reverse("accounts:api-password-reset-confirm", kwargs={"uidb64": uidb64, "token": invalid_token}), {})
        self.assertEqual(response.status_code, 400)
        self.assertIn("Reset link has expired or is invalid", response.json()["error"])

    def test_password_reset_confirm_success(self):
        """Test successful password reset."""
        uidb64 = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)
        reset_url = reverse("accounts:api-password-reset-confirm", kwargs={"uidb64": uidb64, "token": token})

        response = self.client.post(reset_url, {"new_password1": "NewPassword123!", "new_password2": "NewPassword123!"}, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertIn("Password reset successfully", response.json()["detail"])

        # Ensure password is actually updated
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password("NewPassword123!"))

    def test_password_reset_confirm_mismatched_passwords(self):
        """Test password reset with mismatched passwords."""
        uidb64 = urlsafe_base64_encode(force_bytes(self.user.pk))
        token = default_token_generator.make_token(self.user)

        response = self.client.post(reverse("accounts:api-password-reset-confirm", kwargs={"uidb64": uidb64, "token": token}), {
            "new_password1": "NewPassword123!",
            "new_password2": "WrongPassword123!"
        }, format="json")

        self.assertEqual(response.status_code, 400)
        self.assertIn("Passwords do not match", response.json()["error"])
