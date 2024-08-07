from .serializers import ChatMessageSerializer
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import authentication_classes, permission_classes, api_view
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import JSONParser
from django.http import JsonResponse
from .models import ChatMessage
from langchain.memory.chat_message_histories.in_memory import ChatMessageHistory
from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain
from langchain_community.llms.ollama import Ollama
from datetime import timedelta
from django.utils import timezone


llm = Ollama(model="orca-mini")
memory = ConversationBufferMemory()

def retrieve_conversation(user):
    LAST_N_CONVERSATIONS = 4
    conversation = user.conversation
    conversation_context = ChatMessage.objects.filter(
        conversation=conversation
    ).order_by('-timestamp')[:LAST_N_CONVERSATIONS:-1]
    for msg in conversation_context:
        memory.save_context({"input": msg.user_response}, {"output": msg.ai_response})
    retrieved_chat_history = ChatMessageHistory(
        messages=memory.chat_memory.messages
    )
    return retrieved_chat_history


def store_message(user_response, ai_response, conversation_id):
    ChatMessage.objects.create(
        user_response=user_response,
        ai_response=ai_response,
        conversation_id=conversation_id,
    )

@csrf_exempt
@api_view(['POST', 'GET'])
@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
def chat(request):
    if request.method == 'GET':
        request_data = JSONParser().parse(request)
        user = request._user
        conversation = user.conversation
        LAST_N_HRS = timezone.now() - timedelta(hours=60)
        chat_obj = ChatMessage.objects.filter(conversation=conversation).order_by('timestamp').filter(timestamp__gte=LAST_N_HRS)
        chat = ChatMessageSerializer(chat_obj, many=True)
        return JsonResponse(chat.data, safe=False)

    elif request.method == 'POST':
        request_data = JSONParser().parse(request)
        prompt = request_data.get('prompt')
        user = request._user
        retrieved_chat_history = retrieve_conversation(user)
        reloaded_chain = ConversationChain(
            llm=llm,
            memory=ConversationBufferMemory(
                chat_memory=retrieved_chat_history),
            verbose=True
        )
        response = reloaded_chain.predict(input=prompt)
        conversation_id = user.conversation.id
        store_message(prompt, response, conversation_id)
        return JsonResponse({'ai_response': response}, status=201)
