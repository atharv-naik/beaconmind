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
    chat_session, is_new_session = ConversationService.get_or_create_chat_session(conversation)
    chatbot_service = ChatbotService(conversation, chat_session)

    if request.method == 'GET':
        # chat_obj = chatbot_service.chat_history_service.retrieve_chat_history()
        # chat_obj = chatbot_service.chat_history_service.chat_filter({})
        chat_obj = chatbot_service.chat_history_service.retrieve_chat_history_from_session()
        chat = ChatMessageSerializer(chat_obj, many=True)
        return Response({'data': chat.data, 'session': {'id': chat_session.id, 'is_new': is_new_session}}, status=200)
    
    elif request.method == 'POST':
        user_response = request.data.get('query', '')
        if not user_response:
            return Response({'error': 'Invalid request'}, status=400)
        try:
            response = chatbot_service.invoke_chains(user_response)
        except Exception as e:
            return Response({'error': e}, status=500)
        return Response({'ai_response': response}, status=200)
    
    return Response({'error': 'Invalid request'}, status=400)

@login_required
def home(request):
    user = request.user
    if user.role == 'patient':
        return render(request, 'chatbot.html', {'user': user})
    elif user.role == 'doctor':
        return HttpResponse('Doctor Dashboard')
    return redirect('admin:index')

@api_view(['GET'])
def test(request):
    from langchain_core.chat_history import (
        BaseChatMessageHistory,
        InMemoryChatMessageHistory,
    )
    from langchain_core.runnables.history import RunnableWithMessageHistory
    from .chains import ChainStore

    store = {}

    chain = ChainStore.assessment_chain

    def get_session_history(session_id: str) -> BaseChatMessageHistory:
        if session_id not in store:
            store[session_id] = InMemoryChatMessageHistory()
        return store[session_id]
    
    runnable_with_message_history = RunnableWithMessageHistory(
            chain,
            get_session_history=get_session_history,
            input_messages_key="input",
            history_messages_key="history",
            output_messages_key="output",
        )
    
    def bot(input_text: str, session_id: str):
        response = runnable_with_message_history.invoke(
                {"input": input_text},
                config={"configurable": {"session_id": session_id}},
            )
        return response
    
    depressive_msg = "i am feeling very exited lately. i am starting my college journey this year.."
    response = bot(depressive_msg, 'test')
    print(response)
    # return response json
    return Response({'response': response}, status=200)
