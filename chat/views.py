from .serializers import ChatMessageSerializer
from rest_framework.decorators import authentication_classes, permission_classes, api_view
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import render
from rest_framework.response import Response
from .services import ConversationService, ChatbotService
from django.contrib.auth.decorators import login_required


@api_view(['POST', 'GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def chat(request):
    user = request._user
    conversation = ConversationService.get_or_create_conversation(user)
    conversation_id = conversation.id
    chatbot_service = ChatbotService(conversation_id)

    if request.method == 'GET':
        chat_obj = chatbot_service.chat_history_service.retrieve_chat_history()
        chat = ChatMessageSerializer(chat_obj, many=True)
        return Response({'data': chat.data}, status=200)
    
    elif request.method == 'POST':
        user_response = request.data.get('query')
        chat_message = chatbot_service.save_user_message(user_response)
        ai_response = chatbot_service.generate_ai_response(user_response)
        chat_message = chatbot_service.save_ai_message(chat_message, ai_response)
        return Response({'ai_response': ai_response.content}, status=201)
    
    return Response({'error': 'Invalid request'}, status=400)

@login_required
def home(request):
    user = request.user
    return render(request, 'chatbot.html', {'user': user})
