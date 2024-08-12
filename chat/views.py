from .serializers import ChatMessageSerializer
from rest_framework.decorators import authentication_classes, permission_classes, api_view
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import render
from rest_framework.response import Response
from .models import ChatMessage, Conversation
from langchain.memory.chat_message_histories.in_memory import ChatMessageHistory
from langchain.memory import ConversationBufferMemory
from langchain_core.runnables.history import RunnableWithMessageHistory
from .chains import Chains
from datetime import timedelta
from django.utils import timezone
from django.contrib.auth.decorators import login_required


LAST_N_CONVERSATIONS = 4

def get_session_history(conversation_id):
    memory = ConversationBufferMemory()
    conversation_context = ChatMessage.objects.filter(
        conversation_id=conversation_id
    ).order_by('-timestamp')[:LAST_N_CONVERSATIONS:-1]
    for msg in conversation_context:
        memory.save_context({"input": msg.user_response},
                            {"output": msg.ai_response})
    retrieved_chat_history = ChatMessageHistory(
        messages=memory.chat_memory.messages
    )
    return retrieved_chat_history

@api_view(['POST', 'GET'])
@authentication_classes([SessionAuthentication, TokenAuthentication])
@permission_classes([IsAuthenticated])
def chat(request):
    user = request._user
    conversation, _ = Conversation.objects.get_or_create(user=user)
    conversation_id = conversation.id

    if request.method == 'GET':
        LAST_N_HRS = timezone.now() - timedelta(hours=60)
        chat_obj = ChatMessage.objects.filter(conversation_id=conversation_id).order_by(
            'timestamp').filter(timestamp__gte=LAST_N_HRS)
        chat = ChatMessageSerializer(chat_obj, many=True)
        return Response({'data': chat.data}, status=200)
    
    elif request.method == 'POST':
        user_response = request.data.get('query')
        runnable_with_message_history = RunnableWithMessageHistory(
            Chains.default_chain,
            get_session_history,
            input_messages_key="input",
            history_messages_key="history",
        )
        ai_response = runnable_with_message_history.invoke(
            {"input": user_response},
            config={"configurable": {"session_id": conversation_id}},
        )
        ChatMessage.objects.create(
            user_response=user_response,
            ai_response=ai_response.content,
            conversation_id=conversation_id,
            meta_data=ai_response.response_metadata,
        )
        return Response({'ai_response': ai_response.content}, status=201)
    
    return Response({'error': 'Invalid request'}, status=400)

@login_required
def chatbot(request):
    user = request.user
    return render(request, 'chatbot.html', {'user': user})
