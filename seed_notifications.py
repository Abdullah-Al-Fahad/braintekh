import os
import django
import random

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.contrib.auth import get_user_model
from notifications.models import Notification, NotificationType

User = get_user_model()

def seed_notifications():
    print("Seeding dummy notifications...")
    
    # Get all users (or just the first few to keep it quick)
    users = User.objects.all()
    
    if not users.exists():
        print("No users found! Please create a user first.")
        return

    count = 0
    for user in users:
        # Check if user already has notifications to avoid spamming
        if Notification.objects.filter(recipient=user).count() > 5:
            continue
            
        # 1. System Welcome Notification
        Notification.objects.create(
            recipient=user,
            title="Welcome to Braintekh!",
            message="We are thrilled to have you on board. Complete your profile to get started.",
            notification_type=NotificationType.SYSTEM,
            is_read=False
        )
        
        # 2. Profile Verification
        Notification.objects.create(
            recipient=user,
            title="Profile Verified",
            message="Your account has been successfully verified by our compliance team.",
            notification_type=NotificationType.PROFILE_VERIFIED,
            is_read=True
        )
        
        # 3. Collaboration Request
        Notification.objects.create(
            recipient=user,
            title="New Collaboration Request",
            message="An investor is interested in 'AI Medical Assistant'. Review their profile.",
            notification_type=NotificationType.COLLAB_REQUEST,
            related_object_id="101",
            is_read=False
        )
        
        # 4. Unread Message
        Notification.objects.create(
            recipient=user,
            title="New Message from David",
            message="David: 'Can we schedule a quick call to discuss the financials?'",
            notification_type=NotificationType.MESSAGE,
            related_object_id="42",
            is_read=False
        )
        
        count += 4

    print(f"Successfully seeded {count} dummy notifications!")

if __name__ == '__main__':
    seed_notifications()
