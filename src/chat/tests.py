from django.test import TestCase
from django.urls import reverse
from rest_framework.test import APITestCase, APIClient
from rest_framework import status
from django.contrib.auth import get_user_model
from .models import Conversation, ChatMessage, ChatSession
from assessments.definitions import PhaseMap
from rest_framework.authtoken.models import Token
from assessments import definitions
import random

User = get_user_model()


class ChatFromWebTests(TestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser', password='testpass', role='patient')
        self.client.login(username='testuser', password='testpass')
        self.conversation = Conversation.objects.create(user=self.user)
        self.chat_session = ChatSession.objects.create(
            conversation=self.conversation,
            phase=PhaseMap.first(),
            node_id=PhaseMap.get_first().base_node_id,
            init=True
        )

    def test_home_view(self):
        url = reverse('chat:home')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTemplateUsed(response, 'chat/home.html')

    def test_chat_view_get(self):
        url = reverse('chat:chat')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data', response.data)
        self.assertIn('session', response.data)

    def test_chat_view_post_valid(self):
        url = reverse('chat:chat')
        data = {'query': 'Hello'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('ai_response', response.data)
        self.assertIn('session', response.data)

        self.assertEqual(ChatMessage.objects.filter(
            conversation=self.conversation).last().user_response, 'Hello')
        self.assertEqual(ChatMessage.objects.filter(
            conversation=self.conversation).last().ai_response, response.data['ai_response'])


class ChatFromMobileTests(APITestCase):

    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='testuser', password='testpass', role='patient')
        self.token = Token.objects.create(user=self.user)
        self.client.credentials(HTTP_AUTHORIZATION='Token ' + self.token.key)
        self.conversation = Conversation.objects.create(user=self.user)
        self.chat_session = ChatSession.objects.create(
            conversation=self.conversation,
            phase=PhaseMap.first(),
            node_id=PhaseMap.get_first().base_node_id,
            init=True
        )

    def test_get_chat_history(self):
        url = reverse('chat:chat')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('data', response.data)
        self.assertIn('session', response.data)

    def test_post_chat_message(self):
        url = reverse('chat:chat')
        data = {'query': 'Hello'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('ai_response', response.data)
        self.assertIn('session', response.data)

        self.assertEqual(ChatMessage.objects.filter(
            conversation=self.conversation).last().user_response, 'Hello')
        self.assertEqual(ChatMessage.objects.filter(
            conversation=self.conversation).last().ai_response, response.data['ai_response'])

    def test_post_with_invalid_token(self):
        self.client.credentials(HTTP_AUTHORIZATION='Token invalid_token')
        url = reverse('chat:chat')
        data = {'query': 'Hello'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_session_node_id_progress_on_normal_message(self):
        url = reverse('chat:chat')
        while self.chat_session.phase != definitions.END:
            random_node_id = random.choice(
                list(PhaseMap.get(self.chat_session.phase).questions.keys()))
            self.chat_session.node_id = random_node_id
            self.chat_session.retries = 0
            self.chat_session.save(
                update_fields=['phase', 'node_id', 'retries'])
            self.chat_session.refresh_from_db()

            self.assertEqual(self.chat_session.node_id, random_node_id)

            curr_node_id = self.chat_session.node_id
            curr_phase = PhaseMap.get(self.chat_session.phase)

            if self.chat_session.init:
                data = {'query': 'Hello'}
                response = self.client.post(url, data, format='json')
                self.assertEqual(response.status_code, status.HTTP_200_OK)

            data = {'query': 'yes'}
            response = self.client.post(url, data, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.chat_session.refresh_from_db()
            node_after_y = curr_phase.next_q(curr_node_id, 'y', r=0).node_id
            if node_after_y != definitions.END:
                self.assertNotEqual(self.chat_session.node_id, curr_node_id,
                                    f'phase: {self.chat_session.phase}, user_msg: {data["query"]}, ai_msg: {response.data["ai_response"]}, tr=y marker={ChatMessage.objects.filter(conversation=self.conversation).last().user_marker}')
                self.assertEqual(self.chat_session.node_id, node_after_y,
                                f'phase: {self.chat_session.phase}, user_msg: {data["query"]}, ai_msg: {response.data["ai_response"]}, tr=y marker={ChatMessage.objects.filter(conversation=self.conversation).last().user_marker}')
            curr_node_id = self.chat_session.node_id

            data = {'query': 'no'}
            response = self.client.post(url, data, format='json')
            self.assertEqual(response.status_code, status.HTTP_200_OK)
            self.chat_session.refresh_from_db()
            node_after_n = curr_phase.next_q(curr_node_id, 'n', r=0).node_id
            if node_after_n != definitions.END:
                self.assertNotEqual(self.chat_session.node_id, curr_node_id, 
                                    f'phase: {self.chat_session.phase}, user_msg: {data["query"]}, ai_msg: {response.data["ai_response"]}, tr=n marker={ChatMessage.objects.filter(conversation=self.conversation).last().user_marker}')
                self.assertEqual(self.chat_session.node_id, node_after_n, 
                                f'phase: {self.chat_session.phase}, user_msg: {data["query"]}, ai_msg: {response.data["ai_response"]}, tr=n marker={ChatMessage.objects.filter(conversation=self.conversation).last().user_marker}')

            self.chat_session.phase = PhaseMap.next(self.chat_session.phase)
            self.chat_session.save(update_fields=['phase'])
            self.chat_session.refresh_from_db()

        self.assertEqual(self.chat_session.phase, definitions.END)
