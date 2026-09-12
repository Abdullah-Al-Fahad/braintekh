from typing import List
from django.db import transaction
from django.db.models import QuerySet
from notifications.models import Notification, NotificationType
from .models import CollaborationRequest, CollaborationRequestStatus, Project

class CollaborationService:
    """
    Business logic for collaboration requests.
    """

    @staticmethod
    @transaction.atomic
    def bulk_confirm_investors(project: Project, request_ids: List[int]) -> int:
        """
        Confirms a list of approved collaboration requests and sends notifications.
        Returns the number of successfully confirmed requests.
        """
        # Get only the APPROVED requests for this project that match the IDs
        approved_requests = CollaborationRequest.objects.filter(
            project=project,
            id__in=request_ids,
            status=CollaborationRequestStatus.APPROVED
        ).select_related('investor__user')
        
        count = 0
        for collab_req in approved_requests:
            # Transition to CONFIRMED
            collab_req.status = CollaborationRequestStatus.CONFIRMED
            collab_req.save(update_fields=['status'])
            
            # Create a system notification for the investor
            Notification.objects.create(
                recipient=collab_req.investor.user,
                notification_type=NotificationType.SYSTEM,
                title="Investment Confirmed",
                message=f"You have been officially confirmed as an investor for {project.title}.",
                related_object_id=str(project.id)
            )
            count += 1
            
        return count
