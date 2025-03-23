from django.shortcuts import render
from chat.models import ChatMessage, ChatSession, Conversation
from .serializers import ChatMessageSerializer, ChatSessionSerializer, ChatMessageAllSerializer
from rest_framework.decorators import authentication_classes, permission_classes, api_view
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .services.conversation import ConversationManager
from .services.session import SessionPipeline
from .services.constants import Actions
from django.contrib.auth.decorators import permission_required


@permission_required('accounts.can_perform_chat', raise_exception=True)
def home(request):
    return render(request, 'chat/home.html')


@permission_required('accounts.can_view_chat_session', raise_exception=True)
def session_page(request, session_id):
    session = ChatSession.objects.get(id=session_id)
    return render(request, 'chat/session.html', {'session': session})

@api_view(['GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
@permission_required('accounts.can_view_chat_session', raise_exception=True)
def session(request, session_id):
    conversation = Conversation.objects.get(chatsession__id=session_id)
    chat_session = ChatSession.objects.get(id=session_id)
    chat_obj = ChatMessage.objects.filter(conversation_id=conversation.id, chat_session_id=chat_session.id).order_by('timestamp')
    chat = ChatMessageAllSerializer(chat_obj, many=True)
    session_data = ChatSessionSerializer(chat_session)
    return Response({'data': chat.data, 'session': session_data.data}, status=200)


@api_view(['POST', 'GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
@permission_required('accounts.can_perform_chat', raise_exception=True)
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
        action_flag = Actions.get_action_flag(chat_session.status)
        return Response({'data': chat.data, 'session': session_data.data, 'action_flag': action_flag}, status=200)

    elif request.method == 'POST':
        user_response = request.data.get('query', '')
        if not user_response:
            return Response({'error': 'Invalid request'}, status=400)
        try:
            response, chat_state = pipeline.trigger_pipeline(user_response)
            action_flag = Actions.get_action_flag(chat_state)
        except Exception as e:
            return Response({'error': e}, status=500)
        return Response({
                'ai_response': response,
                'session': session_data.data,
                'action_flag': action_flag,
            },
            status=200
        )

    return Response({'error': 'Invalid request'}, status=400)
