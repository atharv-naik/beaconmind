from django.shortcuts import render
from accounts.decorators import allow_only
from .serializers import ChatMessageSerializer, ChatSessionSerializer
from rest_framework.decorators import authentication_classes, permission_classes, api_view
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .services.conversation import ConversationManager
from .services.session import SessionPipeline


@allow_only(['patient'])
def home(request):
    return render(request, 'chat/home.html')


@api_view(['POST', 'GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
@allow_only(['patient'])
def chat(request):
    user = request._user
    conversation, _ = ConversationManager.get_or_create_conversation(user)
    chat_session, _ = ConversationManager.get_or_create_chat_session(conversation)
    session_data = ChatSessionSerializer(chat_session)
    pipeline = SessionPipeline(conversation, chat_session)

    if request.method == 'GET':
        # chat_obj = pipeline.history_manager.get_full_qs()
        chat_obj = pipeline.history_manager.get_from_session()
        chat = ChatMessageSerializer(chat_obj, many=True)
        return Response({'data': chat.data, 'session': session_data.data}, status=200)

    elif request.method == 'POST':
        user_response = request.data.get('query', '')
        if not user_response:
            return Response({'error': 'Invalid request'}, status=400)
        try:
            response = pipeline.trigger_pipeline(user_response)
        except Exception as e:
            return Response({'error': e}, status=500)
        return Response({'ai_response': response, 'session': session_data.data}, status=200)

    return Response({'error': 'Invalid request'}, status=400)
