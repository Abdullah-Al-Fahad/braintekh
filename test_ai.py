import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from ai.services import GeminiAIService
from ai.models import AIConversation
from users.models import User

# Get admin user
user = User.objects.get(email='admin@braintekh.com')

# Start a conversation
conv = AIConversation.objects.create(user=user)
service = GeminiAIService()

print("Step 1 (Init):")
service.handle_conversation_step(conv)
print(conv.step)

print("\nStep 2 (Industry):")
service.handle_conversation_step(conv, "Technology")
print(conv.step)
print(conv.extracted_data)

print("\nStep 3 (Description):")
service.handle_conversation_step(conv, "An AI powered platform for smart agriculture")
print(conv.step)
print(conv.extracted_data)

print("\nStep 4 (Funding):")
service.handle_conversation_step(conv, "5000000")
print(conv.step)
print(conv.extracted_data.get('draft'))
