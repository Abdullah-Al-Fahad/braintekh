from django.urls import path

from .views import (
    DocumentUploadView,
    IndustryListView,
    InvestorOnboardingView,
    SetRoleView,
    SponsorOnboardingView,
    VerificationStatusView,
    PublicProfileDetailView,
    ToggleSavedProfileView,
    SavedProfileListView,
    VerificationDocumentUploadView,
    SponsorNDAView
)

app_name = "profiles"

urlpatterns = [
    # Role selection (step 1 after email verification)
    path("set-role/", SetRoleView.as_view(), name="set-role"),

    # Reference data
    path("industries/", IndustryListView.as_view(), name="industries"),

    # Investor onboarding
    path("investor/onboarding/", InvestorOnboardingView.as_view(), name="investor-onboarding"),

    # Sponsor onboarding
    path("sponsor/", SponsorOnboardingView.as_view(), name="sponsor-onboarding"),
    path("sponsor/status/", VerificationStatusView.as_view(), name="sponsor-status"),
    path("sponsor/nda/", SponsorNDAView.as_view(), name="sponsor-nda"),
    path("verification-documents/", VerificationDocumentUploadView.as_view(), name="verification-documents"),
    path("documents/upload/", DocumentUploadView.as_view(), name="document-upload"),

    # Verification status check (maps to "Verification Pending" screen)
    path("verification-status/", VerificationStatusView.as_view(), name="verification-status"),

    # Public profile view
    path("<int:user_id>/", PublicProfileDetailView.as_view(), name="public-profile"),
    
    # Saved profiles
    path("<int:user_id>/save/", ToggleSavedProfileView.as_view(), name="toggle-saved-profile"),
    path("saved/", SavedProfileListView.as_view(), name="saved-profile-list"),
]
