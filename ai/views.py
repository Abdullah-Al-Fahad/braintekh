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
