from django.apps import AppConfig


class NotificationsConfig(AppConfig):
    name = 'notifications'

    def ready(self):
        import os
        import firebase_admin
        from firebase_admin import credentials
        from django.conf import settings
        
        # Initialize Firebase Admin SDK
        if not firebase_admin._apps:
            firebase_cred_path = os.path.join(settings.BASE_DIR, 'firebase.json')
            if os.path.exists(firebase_cred_path):
                cred = credentials.Certificate(firebase_cred_path)
                firebase_admin.initialize_app(cred)
