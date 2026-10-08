import logging
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, generics, filters
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from drf_spectacular.utils import extend_schema, OpenApiResponse, OpenApiParameter

from core.permissions import IsEmailVerified, IsInvestor, IsSponsor
from core.responses import success_response, created_response, error_response
from notifications.models import Notification, NotificationType
from .models import (
    Category, Project, ProjectTeamMember, ProjectDocument, 
    CollaborationRequest, ProjectStatusChoices, CollaborationRequestStatus,
    SavedProject
)
from .serializers import (
    CategorySerializer, ProjectListSerializer, ProjectDetailSerializer, 
    ProjectCreateUpdateSerializer, CollaborationRequestSerializer,
    CollaborationRequestCreateSerializer, ProjectTeamMemberSerializer,
    ProjectDocumentSerializer, NDASignatureSerializer
)
from .services import CollaborationService

logger = logging.getLogger(__name__)

# --- Public Endpoints ---

@extend_schema(
    tags=["Projects"],
    summary="Public Project Discover Feed",
    description="Returns a paginated list of public, active projects. Supports filtering by industry and search.",
    parameters=[
        OpenApiParameter(name="search", description="Search projects by title or description", required=False, type=str),
        OpenApiParameter(name="industry", description="Filter by industry ID", required=False, type=int),
    ],
    responses={200: ProjectListSerializer(many=True)}
)
class PublicProjectListView(generics.ListAPIView):
    """
    GET /api/v1/projects/
    Publicly accessible list of ACTIVE, FUNDED, or COMPLETED projects.
    Supports filtering by industry and searching by title/location.
    """
    permission_classes = (AllowAny,)
    serializer_class = ProjectListSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['industry__name']
    search_fields = ['title', 'location', 'country']
    ordering_fields = ['created_at', 'funding_goal', 'target_roi']
    ordering = ['-created_at']

    def get_queryset(self):
        return Project.objects.filter(status__in=[
            ProjectStatusChoices.ACTIVE, 
            ProjectStatusChoices.FUNDED,
            ProjectStatusChoices.COMPLETED
        ]).select_related('sponsor__user', 'industry').prefetch_related('categories')


class DiscoverProjectListView(APIView):
    """
    GET /api/v1/projects/discover/
    """
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        queryset = Project.objects.filter(status__in=[
            ProjectStatusChoices.ACTIVE, 
            ProjectStatusChoices.FUNDED,
            ProjectStatusChoices.COMPLETED
        ]).select_related('sponsor__user', 'industry').prefetch_related('categories')
        
        category = request.query_params.get('category')
        if category and category.lower() != 'all':
            queryset = queryset.filter(industry__name__iexact=category)
            
        search = request.query_params.get('search')
        if search:
            queryset = queryset.filter(Q(title__icontains=search) | Q(location__icontains=search))
            
        min_roi = request.query_params.get('min_roi')
        if min_roi:
            queryset = queryset.filter(target_roi__gte=min_roi)
            
        max_roi = request.query_params.get('max_roi')
        if max_roi:
            queryset = queryset.filter(target_roi__lte=max_roi)
            
        min_raise = request.query_params.get('min_raise')
        if min_raise:
            queryset = queryset.filter(funding_goal__gte=min_raise)
            
        max_raise = request.query_params.get('max_raise')
        if max_raise:
            queryset = queryset.filter(funding_goal__lte=max_raise)
            
        sort_by = request.query_params.get('sort_by')
        if sort_by == 'highest_roi':
            queryset = queryset.order_by('-target_roi')
        elif sort_by == 'lowest_roi':
            queryset = queryset.order_by('target_roi')
        elif sort_by == 'highest_raise':
            queryset = queryset.order_by('-funding_goal')
        elif sort_by == 'lowest_raise':
            queryset = queryset.order_by('funding_goal')
        elif sort_by == 'newest':
            queryset = queryset.order_by('-created_at')
        else:
            queryset = queryset.order_by('-created_at')
            
        from django.core.paginator import Paginator
        page_num = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        paginator = Paginator(queryset, page_size)
        page = paginator.get_page(page_num)
        
        serializer = ProjectListSerializer(page.object_list, many=True, context={'request': request})
        
        return success_response(data={
            "count": paginator.count,
            "next": f"/api/v1/projects/discover/?page={page.next_page_number()}" if page.has_next() else None,
            "previous": f"/api/v1/projects/discover/?page={page.previous_page_number()}" if page.has_previous() else None,
            "results": serializer.data
        })


@extend_schema(
    tags=["Projects"],
    summary="Public Project Details",
    description="Returns the full details of a single public project.",
    responses={200: ProjectDetailSerializer}
)
class PublicProjectDetailView(generics.RetrieveAPIView):
    """
    GET /api/v1/projects/<id>/
    Publicly accessible project details. Confidential documents are hidden
    unless the requester is an investor who signed the NDA.
    """
    permission_classes = (AllowAny,)
    serializer_class = ProjectDetailSerializer
    queryset = Project.objects.select_related('sponsor__user', 'industry').prefetch_related(
        'categories', 'team_members', 'documents'
    )

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context


# --- Sponsor Endpoints ---

@extend_schema(
    tags=["Sponsor Projects"],
    summary="List / Create Sponsor Projects",
    description="GET: Lists all projects owned by the authenticated Sponsor.\nPOST: Creates a new project draft.",
    request=ProjectCreateUpdateSerializer,
    responses={
        200: ProjectListSerializer(many=True),
        201: ProjectDetailSerializer
    }
)
class SponsorProjectListView(APIView):
    """
    GET /api/v1/projects/sponsor/
    POST /api/v1/projects/sponsor/
    Sponsor's dashboard: view their own projects or create a new one.
    """
    permission_classes = (IsAuthenticated, IsEmailVerified, IsSponsor)
    parser_classes = (MultiPartParser, FormParser) # For cover_image upload

    def get(self, request):
        status_filter = request.query_params.get('status', 'all').lower()
        projects = Project.objects.filter(sponsor=request.user.sponsor_profile).order_by('-created_at')
        
        if status_filter == 'active':
            projects = projects.filter(status__in=[ProjectStatusChoices.ACTIVE])
        elif status_filter == 'completed':
            projects = projects.filter(status__in=[ProjectStatusChoices.COMPLETED, ProjectStatusChoices.FUNDED])
        elif status_filter == 'terminated':
            projects = projects.filter(status__in=[ProjectStatusChoices.TERMINATED, ProjectStatusChoices.CANCELLED])
            
        serializer = ProjectListSerializer(projects, many=True)
        return success_response(data=serializer.data)

    def post(self, request):
        serializer = ProjectCreateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = serializer.save(sponsor=request.user.sponsor_profile)
        logger.info("Project created by Sponsor: %s", request.user.email)
        return created_response(data=ProjectDetailSerializer(project, context={'request': request}).data, message="Project created successfully.")


@extend_schema(
    tags=["Sponsor Projects"],
    summary="Update / Delete Sponsor Project",
    description="Updates (PATCH) or Deletes (DELETE) a project owned by the sponsor.",
    request=ProjectCreateUpdateSerializer,
    responses={
        200: ProjectDetailSerializer,
        204: OpenApiResponse(description="Deleted")
    }
)
class SponsorProjectDetailView(APIView):
    """
    PATCH /api/v1/projects/sponsor/<id>/
    Sponsor updates their own project.
    """
    permission_classes = (IsAuthenticated, IsEmailVerified, IsSponsor)
    parser_classes = (MultiPartParser, FormParser)

    def patch(self, request, pk):
        project = get_object_or_404(Project, pk=pk, sponsor=request.user.sponsor_profile)
        serializer = ProjectCreateUpdateSerializer(project, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        logger.info("Project updated by Sponsor: %s", request.user.email)
        return success_response(data=ProjectDetailSerializer(project, context={'request': request}).data, message="Project updated successfully.")


@extend_schema(
    tags=["Sponsor Projects"],
    summary="Terminate Project",
    description="Soft-terminates a project and notifies all participating investors.",
    request={"application/json": {"type": "object", "properties": {"reason": {"type": "string"}}}},
    responses={200: OpenApiResponse(description="Project terminated successfully.")}
)
class SponsorProjectTerminateView(APIView):
    """
    POST /api/v1/projects/<id>/terminate/
    """
    permission_classes = (IsAuthenticated, IsEmailVerified, IsSponsor)

    def post(self, request, pk):
        from django.utils import timezone
        
        project = get_object_or_404(Project, pk=pk)
        
        if project.sponsor != request.user.sponsor_profile:
            return error_response("You do not have permission to terminate this project.", status=403)
            
        if project.status == ProjectStatusChoices.TERMINATED:
            return error_response("This project is already terminated.", status=400)
            
        reason = request.data.get('reason', '').strip()
        if len(reason) < 10:
            return error_response("Termination reason is required and must be at least 10 characters.", status=400)
            
        project.status = ProjectStatusChoices.TERMINATED
        project.termination_reason = reason
        project.terminated_at = timezone.now()
        project.save(update_fields=['status', 'termination_reason', 'terminated_at'])
        
        # Notify investors
        from notifications.models import FCMDevice, Notification, NotificationType
        import firebase_admin
        from firebase_admin import messaging
        
        investors = set()
        for req in project.collaboration_requests.all():
            investors.add(req.investor.user)
            
        for user in investors:
            Notification.objects.create(
                recipient=user,
                title="Project Terminated",
                message=f'"{project.title}" has been terminated by the sponsor. Reason: {reason}',
                notification_type=NotificationType.SYSTEM,
                related_object_id=str(project.id)
            )
            
            # FCM
            devices = FCMDevice.objects.filter(user=user, is_active=True)
            for device in devices:
                try:
                    msg = messaging.Message(
                        notification=messaging.Notification(
                            title=f"⚠️ Project Terminated: {project.title}",
                            body=f"The sponsor has terminated this project: {reason[:100]}",
                        ),
                        data={"type": "PROJECT_TERMINATED", "project_id": str(project.id)},
                        token=device.token,
                    )
                    messaging.send(msg)
                except Exception as e:
                    logger.error(f"Failed to send FCM to {user.email}: {e}")
                    
        return success_response(
            message="Project has been terminated successfully.",
            data={
                "id": project.id,
                "title": project.title,
                "status": project.status,
                "terminated_at": project.terminated_at,
                "termination_reason": project.termination_reason
            }
        )


@extend_schema(
    tags=["Sponsor Collaboration"],
    summary="List Collaboration Requests",
    description="Returns all collaboration requests made by investors for a specific project.",
    responses={200: CollaborationRequestSerializer(many=True)}
)
class SponsorCollaborationRequestListView(APIView):
    """
    GET /api/v1/projects/sponsor/<project_id>/requests/
    Sponsor views all requests for a specific project.
    """
    permission_classes = (IsAuthenticated, IsEmailVerified, IsSponsor)

    def get(self, request, project_id):
        project = get_object_or_404(Project, pk=project_id, sponsor=request.user.sponsor_profile)
        requests = project.collaboration_requests.all()
        serializer = CollaborationRequestSerializer(requests, many=True)
        return success_response(data=serializer.data)


@extend_schema(
    tags=["Sponsor Collaboration"],
    summary="List All Recent Requests",
    description="Returns all collaboration requests made by investors across all projects owned by this sponsor.",
    responses={200: CollaborationRequestSerializer(many=True)}
)
class SponsorAllCollaborationRequestListView(generics.ListAPIView):
    """
    GET /api/v1/projects/sponsor/requests/
    Sponsor views all requests across all their projects.
    """
    permission_classes = (IsAuthenticated, IsEmailVerified, IsSponsor)
    serializer_class = CollaborationRequestSerializer

    def get_queryset(self):
        # Fetch all requests for any project owned by this sponsor, ordered by newest first
        return CollaborationRequest.objects.filter(
            project__sponsor=self.request.user.sponsor_profile
        ).select_related('project', 'investor__user').order_by('-created_at')


@extend_schema(
    tags=["Sponsor Collaboration"],
    summary="Update Collaboration Request",
    description="Accept or Reject an investor's collaboration request.",
    request={"application/json": {"type": "object", "properties": {"status": {"type": "string", "enum": ["APPROVED", "REJECTED"]}}}},
    responses={200: CollaborationRequestSerializer}
)
class SponsorCollaborationRequestUpdateView(APIView):
    """
    PATCH /api/v1/projects/sponsor/requests/<id>/
    Sponsor approves or rejects a request.
    """
    permission_classes = (IsAuthenticated, IsEmailVerified, IsSponsor)

    def patch(self, request, pk):
        collab_request = get_object_or_404(CollaborationRequest, pk=pk, project__sponsor=request.user.sponsor_profile)
        status_val = request.data.get('status')
        
        if status_val not in dict(CollaborationRequestStatus.choices):
            return error_response("Invalid status.")
            
        collab_request.status = status_val
        collab_request.save(update_fields=['status'])
        
        return success_response(data=CollaborationRequestSerializer(collab_request).data, message="Request updated.")


@extend_schema(
    tags=["Sponsor Collaboration Actions"],
    summary="Approve Collaboration Request",
    description="Transitions request status to APPROVED.",
    request=None,
    responses={200: OpenApiResponse(description="Request approved successfully")}
)
class SponsorCollaborationRequestApproveView(APIView):
    permission_classes = (IsAuthenticated, IsEmailVerified, IsSponsor)

    def post(self, request, pk):
        collab_request = get_object_or_404(CollaborationRequest, pk=pk, project__sponsor=request.user.sponsor_profile)
        collab_request.status = CollaborationRequestStatus.APPROVED
        collab_request.save(update_fields=['status'])
        return success_response(data={'id': collab_request.id, 'status': collab_request.status}, message="Request approved successfully")

@extend_schema(
    tags=["Sponsor Collaboration Actions"],
    summary="Reject Collaboration Request",
    description="Transitions request status to REJECTED.",
    request=None,
    responses={200: OpenApiResponse(description="Request rejected")}
)
class SponsorCollaborationRequestRejectView(APIView):
    permission_classes = (IsAuthenticated, IsEmailVerified, IsSponsor)

    def post(self, request, pk):
        collab_request = get_object_or_404(CollaborationRequest, pk=pk, project__sponsor=request.user.sponsor_profile)
        collab_request.status = CollaborationRequestStatus.REJECTED
        collab_request.save(update_fields=['status'])
        return success_response(data={'id': collab_request.id, 'status': collab_request.status}, message="Request rejected")

@extend_schema(
    tags=["Sponsor Collaboration Actions"],
    summary="Mark Fund Received",
    description="Confirms escrow or funding receipt.",
    request=None,
    responses={200: OpenApiResponse(description="Fund marked as received")}
)
class SponsorCollaborationRequestFundReceivedView(APIView):
    permission_classes = (IsAuthenticated, IsEmailVerified, IsSponsor)

    def post(self, request, pk):
        collab_request = get_object_or_404(CollaborationRequest, pk=pk, project__sponsor=request.user.sponsor_profile)
        # Using CONFIRMED as the internal status for "Received"
        collab_request.status = CollaborationRequestStatus.CONFIRMED
        collab_request.save(update_fields=['status'])
        
        # Also increment the project's raised_amount
        project = collab_request.project
        project.raised_amount += collab_request.proposed_budget
        project.save(update_fields=['raised_amount'])
        
        return success_response(data={'id': collab_request.id, 'status': "RECEIVED"}, message="Fund marked as received")


@extend_schema(
    tags=["Sponsor Collaboration"],
    summary="Bulk Confirm Investors",
    description="Sponsor confirms a list of APPROVED investors. Generates notifications and system chat messages.",
    request={"application/json": {"type": "object", "properties": {"request_ids": {"type": "array", "items": {"type": "integer"}}}}},
    responses={200: OpenApiResponse(description="Investors confirmed successfully.")}
)
class BulkConfirmInvestorsView(APIView):
    """
    POST /api/v1/projects/<id>/confirm-investors/
    Sponsor confirms multiple investors for a project.
    """
    permission_classes = (IsAuthenticated, IsEmailVerified, IsSponsor)

    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        
        # Verify the user is the sponsor of this project
        if project.sponsor.user != request.user:
            return error_response("You do not have permission to modify this project.")
            
        request_ids = request.data.get('request_ids', [])
        if not request_ids or not isinstance(request_ids, list):
            return error_response("A list of 'request_ids' is required.")
            
        count = CollaborationService.bulk_confirm_investors(project, request_ids)
        
        logger.info("Sponsor %s bulk confirmed %d investors for project %s", request.user.email, count, project.id)
        return success_response(message=f"Successfully confirmed {count} investors.")


# --- Investor Endpoints ---

@extend_schema(
    tags=["Investor Collaboration"],
    summary="Create Collaboration Request",
    description="Investor submits a formal proposal (budget and text) to collaborate on a project.",
    request=CollaborationRequestCreateSerializer,
    responses={
        201: CollaborationRequestSerializer,
        400: OpenApiResponse(description="Already requested or invalid data")
    }
)
class InvestorCollaborationRequestCreateView(APIView):
    """
    POST /api/v1/projects/<project_id>/requests/
    Investor submits a new collaboration request for a project.
    """
    permission_classes = (IsAuthenticated, IsEmailVerified, IsInvestor)

    def post(self, request, project_id):
        project = get_object_or_404(Project, pk=project_id)
        investor = request.user.investor_profile
        
        if project.status == ProjectStatusChoices.TERMINATED or project.status == ProjectStatusChoices.CANCELLED:
            return error_response("Project is no longer accepting requests.", status=400)
            
        if project.status not in [ProjectStatusChoices.ACTIVE]:
            return error_response("Can only submit requests for active projects.")
        
        if CollaborationRequest.objects.filter(project=project, investor=investor).exists():
            return error_response("You have already submitted a request for this project.")
            
        serializer = CollaborationRequestCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        collab_request = serializer.save(project=project, investor=investor)
        logger.info("Investor %s submitted request for project %s", request.user.email, project.id)
        
        return created_response(
            data=CollaborationRequestSerializer(collab_request).data, 
            message="Your collaboration request has been submitted successfully."
        )


@extend_schema(
    tags=["Investor Collaboration"],
    summary="Sign NDA",
    description="Investor signs an NDA for an APPROVED collaboration request.",
    request=NDASignatureSerializer,
    responses={200: OpenApiResponse(description="NDA signed successfully.")}
)
class InvestorSignNDAView(APIView):
    """
    POST /api/v1/projects/<project_id>/sign-nda/
    Investor signs the NDA to access confidential documents.
    Accepts digital signature (typed name) and optional signature image.
    """
    permission_classes = (IsAuthenticated, IsEmailVerified, IsInvestor)
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request, project_id):
        project = get_object_or_404(Project, pk=project_id)
        
        if project.status == ProjectStatusChoices.TERMINATED or project.status == ProjectStatusChoices.CANCELLED:
            return error_response("Project is no longer accepting NDAs.", status=400)
            
        investor = request.user.investor_profile
        
        collab_request = CollaborationRequest.objects.filter(project=project, investor=investor).first()
        if not collab_request:
            return error_response("You must submit a collaboration request before signing the NDA.")
            
        if collab_request.nda_signed:
            return error_response("You have already signed the NDA.")
            
        serializer = NDASignatureSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
            
        collab_request.nda_signed = True
        collab_request.nda_digital_signature = serializer.validated_data['digital_signature']
        
        signature_image = serializer.validated_data.get('signature_image')
        if signature_image:
            collab_request.nda_signature_image = signature_image
            
        collab_request.save(update_fields=['nda_signed', 'nda_digital_signature', 'nda_signature_image'])
        
        logger.info("Investor %s signed NDA for project %s", request.user.email, project.id)
        return success_response(message="NDA signed successfully. You now have access to confidential documents.")


@extend_schema(
    tags=["Investor Collaboration"],
    summary="My Requests",
    description="Returns a list of all collaboration requests the authenticated investor has made.",
    responses={200: CollaborationRequestSerializer(many=True)}
)
class InvestorMyRequestsListView(APIView):
    """
    GET /api/v1/projects/investor/my-requests/
    Investor views all their submitted requests.
    """
    permission_classes = (IsAuthenticated, IsEmailVerified, IsInvestor)

    def get(self, request):
        requests = CollaborationRequest.objects.filter(investor=request.user.investor_profile)
        serializer = CollaborationRequestSerializer(requests, many=True)
        return success_response(data=serializer.data)


# --- Bookmarks Endpoints ---

@extend_schema(
    tags=["Projects"],
    summary="Toggle Bookmark / Save Project",
    description="Saves or unsaves a project for the authenticated user.",
    responses={200: OpenApiResponse(description="Project saved / removed.")}
)
class ToggleSavedProjectView(APIView):
    """
    POST /api/v1/projects/<id>/save/
    Toggle bookmarking a project for the authenticated user.
    """
    permission_classes = (IsAuthenticated,)

    def post(self, request, pk):
        project = get_object_or_404(Project, pk=pk)
        saved_project, created = SavedProject.objects.get_or_create(user=request.user, project=project)
        
        if not created:
            # If it already existed, toggle it off (unsave)
            saved_project.delete()
            return success_response(message="Project removed from saved list.", data={"is_saved": False})
            
        return success_response(message="Project saved successfully.", data={"is_saved": True})


@extend_schema(
    tags=["Projects"],
    summary="Saved Projects Feed",
    description="Returns a paginated list of projects the user has saved.",
    responses={200: ProjectListSerializer(many=True)}
)
class SavedProjectListView(APIView):
    """
    GET /api/v1/projects/saved/
    List all projects bookmarked by the user.
    """
    permission_classes = (IsAuthenticated,)

    def get(self, request):
        saved_items = SavedProject.objects.filter(user=request.user).select_related('project')
        
        status_filter = request.query_params.get('status')
        if status_filter:
            # Map investor-friendly status strings to backend enums if necessary
            pass # simplified for now
            
        from django.core.paginator import Paginator
        page_num = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        paginator = Paginator(saved_items, page_size)
        page = paginator.get_page(page_num)
        
        results = []
        for save_rec in page:
            p = save_rec.project
            # Try to fetch invested amount / value if the user is an investor
            invested_val = 0
            if hasattr(request.user, 'investor_profile'):
                active_request = CollaborationRequest.objects.filter(
                    project=p, 
                    investor=request.user.investor_profile,
                    status=CollaborationRequestStatus.CONFIRMED
                ).first()
                if active_request:
                    invested_val = float(active_request.proposed_budget)
            
            target_roi_val = float(p.target_roi or 0)
            current_value = invested_val * (1 + target_roi_val / 100) if invested_val else 0
            
            results.append({
                "id": str(p.id),
                "saved_item_id": str(save_rec.id),
                "title": p.title,
                "category": p.industry.name if p.industry else "General",
                "saved_date": save_rec.created_at.isoformat(),
                "formatted_date": save_rec.created_at.strftime('%b %d, %Y'),
                "status": p.status,
                "invested": f"${invested_val:,.0f}" if invested_val else "$0",
                "value": f"${current_value:,.0f}" if invested_val else "$0",
                "target_roi": f"+{target_roi_val:.1f}%",
                "funding_progress": float(p.raised_amount) / float(p.funding_goal) if p.funding_goal else 0,
                "image_url": request.build_absolute_uri(p.cover_image.url) if p.cover_image else None
            })
            
        return success_response(data={
            "count": paginator.count,
            "results": results
        })
