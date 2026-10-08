from django.urls import path
from .views import (
    PublicProjectListView, PublicProjectDetailView, DiscoverProjectListView,
    SponsorProjectListView, SponsorProjectDetailView, SponsorProjectTerminateView,
    SponsorCollaborationRequestListView, SponsorAllCollaborationRequestListView, SponsorCollaborationRequestUpdateView,
    SponsorCollaborationRequestApproveView, SponsorCollaborationRequestRejectView, SponsorCollaborationRequestFundReceivedView,
    BulkConfirmInvestorsView,
    InvestorCollaborationRequestCreateView, InvestorSignNDAView, InvestorMyRequestsListView,
    ToggleSavedProjectView, SavedProjectListView
)
from .investor_views import (
    InvestorDashboardView, InvestorInvestmentsView, InvestorPortfolioSummaryView
)

app_name = 'projects'

urlpatterns = [
    # Public (or Authenticated) Endpoints
    path('', PublicProjectListView.as_view(), name='public-project-list'),
    path('discover/', DiscoverProjectListView.as_view(), name='discover-project-list'),
    path('<int:pk>/', PublicProjectDetailView.as_view(), name='public-project-detail'),

    # Sponsor Endpoints
    path('sponsor/', SponsorProjectListView.as_view(), name='sponsor-project-list-create'),
    path('sponsor/<int:pk>/', SponsorProjectDetailView.as_view(), name='sponsor-project-detail-update'),
    path('<int:pk>/terminate/', SponsorProjectTerminateView.as_view(), name='sponsor-project-terminate'),
    path('sponsor/<int:project_id>/requests/', SponsorCollaborationRequestListView.as_view(), name='sponsor-request-list'),
    path('sponsor/requests/', SponsorAllCollaborationRequestListView.as_view(), name='sponsor-all-request-list'),
    path('sponsor/requests/<int:pk>/', SponsorCollaborationRequestUpdateView.as_view(), name='sponsor-request-update'),
    path('sponsor/requests/<int:pk>/approve/', SponsorCollaborationRequestApproveView.as_view(), name='sponsor-request-approve'),
    path('sponsor/requests/<int:pk>/reject/', SponsorCollaborationRequestRejectView.as_view(), name='sponsor-request-reject'),
    path('sponsor/requests/<int:pk>/fund-received/', SponsorCollaborationRequestFundReceivedView.as_view(), name='sponsor-request-fund-received'),
    path('<int:pk>/confirm-investors/', BulkConfirmInvestorsView.as_view(), name='sponsor-bulk-confirm'),

    # Investor Endpoints
    path('investor/dashboard/', InvestorDashboardView.as_view(), name='investor-dashboard'),
    path('investor/investments/', InvestorInvestmentsView.as_view(), name='investor-investments'),
    path('investor/portfolio-summary/', InvestorPortfolioSummaryView.as_view(), name='investor-portfolio-summary'),
    path('<int:project_id>/requests/', InvestorCollaborationRequestCreateView.as_view(), name='investor-request-create'),
    path('<int:project_id>/sign-nda/', InvestorSignNDAView.as_view(), name='investor-sign-nda'),
    path('investor/my-requests/', InvestorMyRequestsListView.as_view(), name='investor-my-requests'),

    # Bookmarks
    path('<int:pk>/save/', ToggleSavedProjectView.as_view(), name='toggle-saved-project'),
    path('saved/', SavedProjectListView.as_view(), name='saved-project-list'),
]
