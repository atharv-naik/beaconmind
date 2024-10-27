from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from django.contrib.auth import get_user_model
from rest_framework.authtoken.models import Token
from .models import Conversation, ChatMessage


User = get_user_model()

class ChatTests(APITestCase):

    def setUp(self):
        self.client = APIClient(enforce_csrf_checks=True)
        self.user = User.objects.create_user(username='testuser', password='testpassword', role='patient')
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        self.conversation = Conversation.objects.create(user=self.user)
        self.chat_url = reverse('chat:chat')

    def test_chat_post(self):
        data = {'query': 'Hello, how are you?'}
        response = self.client.post(self.chat_url, data, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertIn('ai_response', response.data)
        self.assertTrue(ChatMessage.objects.filter(conversation=self.conversation).exists())

    def test_chat_get(self):
        ChatMessage.objects.create(conversation=self.conversation, user_response='Hello', ai_response='Hi')
        response = self.client.get(self.chat_url, format='json')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertIn('user_response', response.data.get('data')[0])
