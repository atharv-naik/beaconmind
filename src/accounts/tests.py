from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
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
        self.password_reset_url = reverse('accounts:api-password-reset')
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
    
    def test_password_reset(self):
        self.client.credentials(HTTP_AUTHORIZATION=f'Token {self.staff_token}')
        data = {'old_password': 'staffpass', 'new_password': 'newstrongpass'}
        response = self.client.post(self.password_reset_url, data, format='json')
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

