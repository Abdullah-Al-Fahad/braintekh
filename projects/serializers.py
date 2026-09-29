from rest_framework import serializers
from .models import (
    Category, Project, ProjectTeamMember, ProjectDocument, 
    CollaborationRequest, ProjectStatusChoices, CollaborationRequestStatus
)
from profiles.serializers import SponsorProfileSerializer, InvestorProfileSerializer

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'name']

class ProjectTeamMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectTeamMember
        fields = ['id', 'name', 'role']
        read_only_fields = ['id']

class ProjectDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectDocument
        fields = ['id', 'title', 'file', 'is_confidential', 'created_at']
        read_only_fields = ['id', 'created_at']

class ProjectListSerializer(serializers.ModelSerializer):
    categories = CategorySerializer(many=True, read_only=True)
    sponsor = serializers.SerializerMethodField()
    is_saved = serializers.SerializerMethodField()

    progress = serializers.SerializerMethodField()
    category = serializers.SerializerMethodField()
    industry = serializers.StringRelatedField() # Make industry a string as requested

    class Meta:
        model = Project
        fields = [
            'id', 'title', 'location', 'country', 'short_description', 'categories', 'category', 'industry',
            'status', 'funding_goal', 'funding_stage', 'raised_amount', 'progress', 'minimum_investment',
            'target_roi', 'potential_monthly_revenue', 'hold_period_months', 
            'timeline_to_operations_months', 'timeline_months', 
            'cover_image', 'sponsor', 'is_saved', 'created_at'
        ]
    
    def get_sponsor(self, obj):
        # Return basic sponsor info
        return {
            'legal_company_name': obj.sponsor.legal_company_name,
            'is_verified': obj.sponsor.verification_status == 'APPROVED',
            'projects_count': obj.sponsor.projects.count()
        }

    def get_is_saved(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.saved_by.filter(user=request.user).exists()
        return False

    def get_progress(self, obj):
        if obj.funding_goal and float(obj.funding_goal) > 0:
            # Safely calculate progress by ensuring both are floats
            prog = float(obj.raised_amount) / float(obj.funding_goal)
            return float(round(prog, 2))
        return 0.0

    def get_category(self, obj):
        cat = obj.categories.first()
        if cat:
            return {"id": cat.id, "name": cat.name}
        return None

class ProjectDetailSerializer(ProjectListSerializer):
    team_members = ProjectTeamMemberSerializer(many=True, read_only=True)
    documents = serializers.SerializerMethodField()
    
    investors_count = serializers.SerializerMethodField()
    pending_review_amount = serializers.SerializerMethodField()
    contributions = serializers.SerializerMethodField()

    class Meta(ProjectListSerializer.Meta):
        fields = ProjectListSerializer.Meta.fields + [
            'business_description', 'current_status', 'next_milestones', 
            'use_of_funds', 'skin_in_the_game', 'team_members', 'team_members_text', 
            'confidentiality_agreement_text', 'documents', 'investors_count', 
            'pending_review_amount', 'contributions'
        ]

    def get_documents(self, obj):
        request = self.context.get('request')
        # If user is sponsor of this project, show all docs
        if request and hasattr(request.user, 'sponsor_profile') and request.user.sponsor_profile == obj.sponsor:
            docs = obj.documents.all()
            return ProjectDocumentSerializer(docs, many=True).data
        
        # If user is investor, check NDA status
        if request and hasattr(request.user, 'investor_profile'):
            investor = request.user.investor_profile
            has_signed_nda = CollaborationRequest.objects.filter(
                project=obj, investor=investor, nda_signed=True
            ).exists()
            
            if has_signed_nda:
                docs = obj.documents.all()
            else:
                docs = obj.documents.filter(is_confidential=False)
            return ProjectDocumentSerializer(docs, many=True).data
            
        # For public/unauthenticated, show only non-confidential
        docs = obj.documents.filter(is_confidential=False)
        return ProjectDocumentSerializer(docs, many=True).data

    def get_investors_count(self, obj):
        return obj.collaboration_requests.filter(status=CollaborationRequestStatus.CONFIRMED).count()
        
    def get_pending_review_amount(self, obj):
        from django.db.models import Sum
        total = obj.collaboration_requests.filter(status=CollaborationRequestStatus.PENDING).aggregate(Sum('proposed_budget'))['proposed_budget__sum']
        return total or 0.00
        
    def get_contributions(self, obj):
        request = self.context.get('request')
        is_sponsor = request and hasattr(request.user, 'sponsor_profile') and request.user.sponsor_profile == obj.sponsor
        
        has_signed_nda = False
        if request and hasattr(request.user, 'investor_profile'):
            has_signed_nda = obj.collaboration_requests.filter(
                investor=request.user.investor_profile, nda_signed=True
            ).exists()
            
        # Only show contributions to the sponsor or investors who have signed the NDA
        if is_sponsor or has_signed_nda:
            contributions = obj.collaboration_requests.filter(status=CollaborationRequestStatus.CONFIRMED)
            return [
                {
                    "investor_name": c.investor.user.full_name,
                    "amount": str(c.proposed_budget),
                    "date": c.created_at
                } for c in contributions
            ]
        return []

class ProjectCreateUpdateSerializer(serializers.ModelSerializer):
    category_ids = serializers.PrimaryKeyRelatedField(
        many=True, queryset=Category.objects.all(), source='categories', required=False
    )
    
    class Meta:
        model = Project
        fields = [
            'title', 'location', 'country', 'short_description', 'category_ids', 'industry',
            'funding_goal', 'funding_stage', 'minimum_investment', 'target_roi', 'timeline_months',
            'potential_monthly_revenue', 'hold_period_months', 'timeline_to_operations_months',
            'business_description', 'current_status', 'next_milestones', 
            'use_of_funds', 'skin_in_the_game', 'team_members_text', 
            'confidentiality_agreement_text', 'cover_image', 'status'
        ]

class CollaborationRequestSerializer(serializers.ModelSerializer):
    investor = serializers.SerializerMethodField()
    project = serializers.SerializerMethodField()

    class Meta:
        model = CollaborationRequest
        fields = [
            'id', 'project', 'investor', 'proposed_budget', 
            'proposal_text', 'status', 'nda_signed', 'nda_digital_signature', 
            'nda_signature_image', 'created_at'
        ]
        read_only_fields = ['id', 'status', 'nda_signed', 'nda_digital_signature', 'nda_signature_image', 'created_at']

    def get_investor(self, obj):
        return {
            'id': obj.investor.id,
            'name': obj.investor.user.full_name,
            'investor_type': obj.investor.investor_type,
            'photo': obj.investor.profile_photo.url if obj.investor.profile_photo else None
        }

    def get_project(self, obj):
        return {
            'id': obj.project.id,
            'title': obj.project.title,
        }

class CollaborationRequestCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = CollaborationRequest
        fields = ['proposed_budget', 'proposal_text']

class NDASignatureSerializer(serializers.Serializer):
    digital_signature = serializers.CharField(max_length=255, required=True)
    signature_image = serializers.ImageField(required=False)

