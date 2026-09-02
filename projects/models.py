from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from core.models import TimeStampedModel
from profiles.models import SponsorProfile, InvestorProfile, Industry

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")
        ordering = ["name"]

    def __str__(self):
        return self.name

class ProjectStatusChoices(models.TextChoices):
    DRAFT = 'DRAFT', _('Draft')
    ACTIVE = 'ACTIVE', _('Active')
    FUNDED = 'FUNDED', _('Funded')
    COMPLETED = 'COMPLETED', _('Completed')
    TERMINATED = 'TERMINATED', _('Terminated')
    CANCELLED = 'CANCELLED', _('Cancelled')

class Project(TimeStampedModel):
    sponsor = models.ForeignKey(SponsorProfile, on_delete=models.CASCADE, related_name='projects')
    title = models.CharField(max_length=255)
    location = models.CharField(max_length=255, help_text="e.g. Austin, TX")
    country = models.CharField(max_length=100, blank=True)
    short_description = models.CharField(max_length=120, help_text="One-line pitch")
    
    industry = models.ForeignKey(Industry, on_delete=models.SET_NULL, null=True, blank=True, related_name='projects')
    categories = models.ManyToManyField(Category, related_name='projects', blank=True) # Keeping for backwards compatibility if needed
    
    # Funding Details
    status = models.CharField(max_length=20, choices=ProjectStatusChoices.choices, default=ProjectStatusChoices.DRAFT, db_index=True)
    funding_goal = models.DecimalField(max_digits=12, decimal_places=2, help_text="Total amount to raise")
    funding_stage = models.CharField(max_length=100, blank=True, help_text="e.g. Seed, Series A")
    raised_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    minimum_investment = models.DecimalField(max_digits=12, decimal_places=2, help_text="Minimum Investment Amount (MIA)")
    
    # Project Metrics
    target_roi = models.DecimalField(max_digits=5, decimal_places=2, help_text="Target ROI percentage (e.g., 18.00 for 18%)")
    potential_monthly_revenue = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    hold_period_months = models.PositiveIntegerField(null=True, blank=True, help_text="Hold period in months")
    timeline_to_operations_months = models.PositiveIntegerField(null=True, blank=True, help_text="Timeline to operations in months")
    timeline_months = models.PositiveIntegerField(help_text="Overall project timeline in months")
    
    # Detailed Description (Details Tab)
    business_description = models.TextField(blank=True, help_text="Full Description")
    current_status = models.TextField(blank=True, verbose_name="What's Happening Now")
    next_milestones = models.TextField(blank=True)
    use_of_funds = models.TextField(blank=True)
    skin_in_the_game = models.DecimalField(max_digits=12, decimal_places=2, default=0.00, help_text="Sponsor's invested amount")
    
    team_members_text = models.CharField(max_length=500, blank=True, help_text="Names, comma separated")
    confidentiality_agreement_text = models.TextField(blank=True, help_text="Detailed explanation of the confidentiality agreement")
    
    cover_image = models.ImageField(upload_to='project_images/', null=True, blank=True)

    class Meta:
        verbose_name = _("Project")
        verbose_name_plural = _("Projects")

    def __str__(self):
        return f"{self.title} ({self.sponsor.legal_company_name or self.sponsor.user.email})"

class ProjectTeamMember(TimeStampedModel):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='team_members')
    name = models.CharField(max_length=255)
    role = models.CharField(max_length=255)
    # Could optionally add a photo field here if needed later

    class Meta:
        verbose_name = _("Project Team Member")
        verbose_name_plural = _("Project Team Members")

    def __str__(self):
        return f"{self.name} - {self.role} ({self.project.title})"

class ProjectDocument(TimeStampedModel):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='documents')
    title = models.CharField(max_length=255)
    file = models.FileField(upload_to='project_documents/')
    is_confidential = models.BooleanField(default=False, help_text="Requires NDA to view")

    class Meta:
        verbose_name = _("Project Document")
        verbose_name_plural = _("Project Documents")

    def __str__(self):
        return f"{self.title} for {self.project.title}"

class CollaborationRequestStatus(models.TextChoices):
    PENDING = 'PENDING', _('Pending')
    APPROVED = 'APPROVED', _('Approved')
    REJECTED = 'REJECTED', _('Rejected')
    CONFIRMED = 'CONFIRMED', _('Confirmed')

class CollaborationRequest(TimeStampedModel):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='collaboration_requests')
    investor = models.ForeignKey(InvestorProfile, on_delete=models.CASCADE, related_name='collaboration_requests')
    
    proposed_budget = models.DecimalField(max_digits=12, decimal_places=2)
    proposal_text = models.TextField(blank=True, help_text="Message from the investor")
    
    status = models.CharField(max_length=20, choices=CollaborationRequestStatus.choices, default=CollaborationRequestStatus.PENDING, db_index=True)
    nda_signed = models.BooleanField(default=False, help_text="Has the investor signed the NDA for this project?")
    nda_digital_signature = models.CharField(max_length=255, blank=True, help_text="Typed full name for NDA signature")
    nda_signature_image = models.ImageField(upload_to='nda_signatures/', null=True, blank=True)

    class Meta:
        verbose_name = _("Collaboration Request")
        verbose_name_plural = _("Collaboration Requests")
        unique_together = ('project', 'investor') # An investor can only have one active request per project (generally)

    def __str__(self):
        return f"Request by {self.investor.user.email} for {self.project.title}"

from django.contrib.auth import get_user_model
User = get_user_model()

class SavedProject(TimeStampedModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='saved_projects')
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='saved_by')

    class Meta:
        verbose_name = _("Saved Project")
        verbose_name_plural = _("Saved Projects")
        unique_together = ('user', 'project')

    def __str__(self):
        return f"{self.user.email} saved {self.project.title}"
