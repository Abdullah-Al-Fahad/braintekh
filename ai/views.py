from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from .models import AIConversation
from .serializers import AIConversationSerializer
from .services import GeminiAIService

class AIConversationView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        service = GeminiAIService()
        conversation = AIConversation.objects.create(user=request.user)
        service.handle_conversation_step(conversation)
        
        serializer = AIConversationSerializer(conversation)
        return Response({
            "status": "success",
            "data": serializer.data
        }, status=status.HTTP_201_CREATED)

class AIConversationDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, pk, *args, **kwargs):
        try:
            conversation = AIConversation.objects.get(id=pk, user=request.user)
            serializer = AIConversationSerializer(conversation)
            return Response({
                "status": "success",
                "data": serializer.data
            })
        except AIConversation.DoesNotExist:
            return Response({"status": "error", "message": "Not found"}, status=status.HTTP_404_NOT_FOUND)

    def delete(self, request, pk, *args, **kwargs):
        try:
            conversation = AIConversation.objects.get(id=pk, user=request.user)
            conversation.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except AIConversation.DoesNotExist:
            return Response({"status": "error", "message": "Not found"}, status=status.HTTP_404_NOT_FOUND)

class AIMessageView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk, *args, **kwargs):
        try:
            conversation = AIConversation.objects.get(id=pk, user=request.user)
        except AIConversation.DoesNotExist:
            return Response({"status": "error", "message": "Not found"}, status=status.HTTP_404_NOT_FOUND)
            
        content = request.data.get('content')
        if not content:
            return Response({"status": "error", "message": "Content required"}, status=status.HTTP_400_BAD_REQUEST)
            
        service = GeminiAIService()
        service.handle_conversation_step(conversation, user_message=content)
        
        serializer = AIConversationSerializer(conversation)
        return Response({
            "status": "success",
            "data": serializer.data
        })

# =============================================================================
# Investment Copilot Views
# =============================================================================

from core.responses import success_response, error_response
from django.core.paginator import Paginator

class CopilotInitialView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        service = GeminiAIService()
        data = service.get_initial_copilot_state(request.user)
        return success_response(data=data)

class CopilotMessageView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, conversation_id, *args, **kwargs):
        try:
            conversation = AIConversation.objects.get(id=conversation_id, user=request.user)
        except AIConversation.DoesNotExist:
            return error_response("Conversation not found", status=status.HTTP_404_NOT_FOUND)
            
        messages = conversation.messages.all().order_by('timestamp')
        
        # Pagination
        page_num = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 30))
        paginator = Paginator(messages, page_size)
        page = paginator.get_page(page_num)
        
        msg_list = []
        for m in page:
            msg_list.append({
                "id": str(m.id),
                "text": m.content,
                "is_user": m.role == 'user',
                "created_at": m.timestamp.isoformat(),
                "suggestions": m.suggestions
            })
            
        return success_response(data={
            "conversation_id": conversation_id,
            "count": paginator.count,
            "messages": msg_list
        })

    def post(self, request, conversation_id, *args, **kwargs):
        try:
            conversation = AIConversation.objects.get(id=conversation_id, user=request.user)
        except AIConversation.DoesNotExist:
            return error_response("Conversation not found", status=status.HTTP_404_NOT_FOUND)
            
        content = request.data.get('content')
        if not content:
            return error_response("Content cannot be empty.", status=status.HTTP_400_BAD_REQUEST)
            
        context = request.data.get('context')
        
        service = GeminiAIService()
        user_msg, ai_msg, quick_prompts = service.handle_copilot_chat(conversation, content, context)
        
        return success_response(data={
            "user_message": {
                "id": str(user_msg.id),
                "text": user_msg.content,
                "is_user": True,
                "created_at": user_msg.timestamp.isoformat()
            },
            "ai_reply": {
                "id": str(ai_msg.id),
                "text": ai_msg.content,
                "is_user": False,
                "created_at": ai_msg.timestamp.isoformat(),
                "suggestions": ai_msg.suggestions
            },
            "updated_quick_prompts": quick_prompts
        })

class CopilotClearView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, conversation_id, *args, **kwargs):
        try:
            conversation = AIConversation.objects.get(id=conversation_id, user=request.user)
            conversation.delete()
        except AIConversation.DoesNotExist:
            pass # Ignore if not found, it's a delete operation anyway
            
        # Create a fresh conversation state
        service = GeminiAIService()
        data = service.get_initial_copilot_state(request.user)
        
        # Format the new state into the response
        return success_response(message="Chat history cleared successfully.", data={
            "new_conversation_id": data['conversation_id'],
            "welcome_message": data['welcome_message']
        })

    # Allow POST as well as specified in the docs (Some clients prefer POST for actions)
    def post(self, request, conversation_id, *args, **kwargs):
        return self.delete(request, conversation_id, *args, **kwargs)
