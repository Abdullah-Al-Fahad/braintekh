from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from core.permissions import IsInvestor, IsEmailVerified
from core.responses import success_response
from projects.models import CollaborationRequest, CollaborationRequestStatus
from django.db.models import Sum, F
from django.core.paginator import Paginator

class InvestorDashboardView(APIView):
    """
    GET /api/v1/investor/dashboard/
    """
    permission_classes = (IsAuthenticated, IsEmailVerified, IsInvestor)

    def get(self, request):
        investor = request.user.investor_profile
        
        active_investments = CollaborationRequest.objects.filter(
            investor=investor,
            status=CollaborationRequestStatus.CONFIRMED
        ).aggregate(
            total_invested=Sum('proposed_budget')
        )
        
        return success_response(data={
            "total_invested": float(active_investments['total_invested'] or 0),
            "active_investments_count": CollaborationRequest.objects.filter(
                investor=investor,
                status=CollaborationRequestStatus.CONFIRMED
            ).count()
        })

class InvestorInvestmentsView(APIView):
    """
    GET /api/v1/investor/investments/
    """
    permission_classes = (IsAuthenticated, IsEmailVerified, IsInvestor)

    def get(self, request):
        investor = request.user.investor_profile
        
        # Get query params
        status_filter = request.query_params.get('status', 'all').lower()
        
        requests = CollaborationRequest.objects.filter(investor=investor).select_related('project__sponsor__user', 'project__industry')
        
        if status_filter == 'active':
            requests = requests.filter(status=CollaborationRequestStatus.CONFIRMED)
        elif status_filter == 'pending':
            requests = requests.filter(status=CollaborationRequestStatus.PENDING)
        elif status_filter == 'completed':
            requests = requests.filter(status=CollaborationRequestStatus.APPROVED)
        elif status_filter == 'cancelled':
            requests = requests.filter(status=CollaborationRequestStatus.REJECTED)
            
        requests = requests.order_by('-created_at')
        
        # Calculate Summary
        active_requests = CollaborationRequest.objects.filter(investor=investor, status=CollaborationRequestStatus.CONFIRMED).select_related('project')
        total_invested = sum([r.proposed_budget for r in active_requests])
        
        # Calculate current value by applying project target_roi to invested amount (simplified for MVP)
        total_current_value = 0
        for r in active_requests:
            roi_multiplier = 1 + (r.project.target_roi / 100) if r.project.target_roi else 1
            total_current_value += float(r.proposed_budget) * float(roi_multiplier)
            
        overall_roi = ((total_current_value - float(total_invested)) / float(total_invested)) * 100 if total_invested else 0
        
        summary = {
            "total_invested": f"${total_invested:,.0f}",
            "total_current_value": f"${total_current_value:,.0f}",
            "overall_roi": f"+{overall_roi:.2f}%",
            "active_investments_count": active_requests.count()
        }
        
        # Pagination
        page_num = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        paginator = Paginator(requests, page_size)
        page = paginator.get_page(page_num)
        
        results = []
        for r in page:
            p = r.project
            roi_val = float(p.target_roi or 0)
            cur_val = float(r.proposed_budget) * (1 + roi_val / 100)
            
            results.append({
                "id": str(r.id),
                "project_id": str(p.id),
                "title": p.title,
                "category": p.industry.name if p.industry else "General",
                "sponsor_name": p.sponsor.legal_company_name or f"{p.sponsor.user.first_name} {p.sponsor.user.last_name}",
                "sponsor_id": str(p.sponsor.user.id),
                "investment_date": r.created_at.isoformat(),
                "formatted_date": r.created_at.strftime('%b %d, %Y'),
                "status": r.get_status_display(),
                "invested_amount": float(r.proposed_budget),
                "formatted_invested": f"${r.proposed_budget:,.0f}",
                "current_value": cur_val,
                "formatted_current_value": f"${cur_val:,.0f}",
                "roi": f"+{roi_val:.1f}%",
                "image_url": request.build_absolute_uri(p.cover_image.url) if p.cover_image else None
            })
            
        return success_response(data={
            "summary": summary,
            "count": paginator.count,
            "next": f"/api/v1/investor/investments/?page={page.next_page_number()}" if page.has_next() else None,
            "previous": f"/api/v1/investor/investments/?page={page.previous_page_number()}" if page.has_previous() else None,
            "results": results
        })

class InvestorPortfolioSummaryView(APIView):
    """
    GET /api/v1/investor/portfolio-summary/
    """
    permission_classes = (IsAuthenticated, IsEmailVerified, IsInvestor)

    def get(self, request):
        # Can reuse the summary logic or return more detailed chart data
        return success_response(data={
            "message": "Portfolio summary API placeholder"
        })
