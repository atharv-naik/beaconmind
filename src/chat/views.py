from django.http import HttpResponse
from .serializers import ChatMessageSerializer
from rest_framework.decorators import authentication_classes, permission_classes, api_view
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import redirect, render
from rest_framework.response import Response
from .services import ConversationService, ChatbotService
from django.contrib.auth.decorators import login_required


@api_view(['POST', 'GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def chat(request):
    user = request._user
    conversation, _ = ConversationService.get_or_create_conversation(user)
    chat_session, _ = ConversationService.get_or_create_chat_session(conversation)
    chatbot_service = ChatbotService(conversation, chat_session)

    if request.method == 'GET':
        chat_obj = chatbot_service.chat_history_service.retrieve_chat_history()
        chat_obj = chatbot_service.chat_history_service.retrieve_chat_history_from_session()
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
    if user.role == 'patient':
        return render(request, 'chatbot.html', {'user': user})
    elif user.role == 'doctor':
        return HttpResponse('Doctor Dashboard')
    return redirect('admin:index')
