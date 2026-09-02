from django.urls import path
from .views import (
    PublicProjectListView, PublicProjectDetailView,
    SponsorProjectListView, SponsorProjectDetailView,
    SponsorCollaborationRequestListView, SponsorCollaborationRequestUpdateView,
    InvestorCollaborationRequestCreateView, InvestorSignNDAView, InvestorMyRequestsListView,
    ToggleSavedProjectView, SavedProjectListView
)

app_name = 'projects'

urlpatterns = [
    # Public (or Authenticated) Endpoints
    path('', PublicProjectListView.as_view(), name='public-project-list'),
    path('<int:pk>/', PublicProjectDetailView.as_view(), name='public-project-detail'),

    # Sponsor Endpoints
    path('sponsor/', SponsorProjectListView.as_view(), name='sponsor-project-list-create'),
    path('sponsor/<int:pk>/', SponsorProjectDetailView.as_view(), name='sponsor-project-detail-update'),
    path('sponsor/<int:project_id>/requests/', SponsorCollaborationRequestListView.as_view(), name='sponsor-project-requests'),
    path('sponsor/requests/<int:pk>/', SponsorCollaborationRequestUpdateView.as_view(), name='sponsor-request-update'),

    # Investor Endpoints
    path('<int:project_id>/requests/', InvestorCollaborationRequestCreateView.as_view(), name='investor-request-create'),
    path('<int:project_id>/sign-nda/', InvestorSignNDAView.as_view(), name='investor-sign-nda'),
    path('investor/my-requests/', InvestorMyRequestsListView.as_view(), name='investor-my-requests'),

    # Bookmarks
    path('<int:pk>/save/', ToggleSavedProjectView.as_view(), name='toggle-saved-project'),
    path('saved/', SavedProjectListView.as_view(), name='saved-project-list'),
]
