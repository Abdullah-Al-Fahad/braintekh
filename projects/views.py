import logging
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import status, generics, filters
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.parsers import MultiPartParser, FormParser
from core.permissions import IsSponsor, IsInvestor, IsEmailVerified
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

class SponsorProjectListView(APIView):
    """
    GET /api/v1/projects/sponsor/
    POST /api/v1/projects/sponsor/
    Sponsor's dashboard: view their own projects or create a new one.
    """
    permission_classes = (IsAuthenticated, IsEmailVerified, IsSponsor)
    parser_classes = (MultiPartParser, FormParser) # For cover_image upload

    def get(self, request):
        status_filter = request.query_params.get('status')
        projects = Project.objects.filter(sponsor=request.user.sponsor_profile)
        if status_filter:
            projects = projects.filter(status=status_filter)
            
        serializer = ProjectListSerializer(projects, many=True)
        return success_response(data=serializer.data)

    def post(self, request):
        serializer = ProjectCreateUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        project = serializer.save(sponsor=request.user.sponsor_profile)
        logger.info("Project created by Sponsor: %s", request.user.email)
        return created_response(data=ProjectDetailSerializer(project, context={'request': request}).data, message="Project created successfully.")


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

class InvestorCollaborationRequestCreateView(APIView):
    """
    POST /api/v1/projects/<project_id>/requests/
    Investor submits a new collaboration request for a project.
    """
    permission_classes = (IsAuthenticated, IsEmailVerified, IsInvestor)

    def post(self, request, project_id):
        project = get_object_or_404(Project, pk=project_id)
        investor = request.user.investor_profile
        
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
            return success_response(message="Project removed from saved list.")
            
        return success_response(message="Project saved successfully.")


class SavedProjectListView(generics.ListAPIView):
    """
    GET /api/v1/projects/saved/
    List all projects bookmarked by the user.
    """
    permission_classes = (IsAuthenticated,)
    serializer_class = ProjectListSerializer

    def get_queryset(self):
        # Return projects related to the user's SavedProject records
        return Project.objects.filter(saved_by__user=self.request.user)
