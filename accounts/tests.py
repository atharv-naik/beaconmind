from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model


User = get_user_model()

class AuthTests(APITestCase):

    def setUp(self):
        self.client = APIClient()
        self.register_url = reverse('accounts:api-register')
        self.auth_url = reverse('accounts:api-get-auth')
        self.user_data = {
            'username': 'testuser',
            'email': 'testuser@example.com',
            'phone': '1234567890',
            'address': '123 Test St',
            'role': 'staff',
            'password': 'testpassword'
        }

    def test_register_user(self):
        response = self.client.post(self.register_url, self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertTrue(User.objects.filter(username='testuser').exists())

    def test_register_doctor(self):
        self.user_data['role'] = 'doctor'
        response = self.client.post(self.register_url, self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username='testuser')
        self.assertEqual(user.role, 'doctor')
        self.assertTrue(hasattr(user, 'doctor'))

    def test_register_patient(self):
        self.user_data['role'] = 'patient'
        response = self.client.post(self.register_url, self.user_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        user = User.objects.get(username='testuser')
        self.assertEqual(user.role, 'patient')
        self.assertTrue(hasattr(user, 'patient'))

    def test_obtain_auth_token(self):
        self.client.post(self.register_url, self.user_data, format='json')
        response = self.client.post(self.auth_url, {
            'username': 'testuser',
            'password': 'testpassword'
        }, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('token', response.data)
