from django.utils.timezone import now, timedelta
from django.db.models import Sum
from users.models import User
from projects.models import Project, ProjectStatusChoices

def dashboard_callback(request, context):
    """
    Callback to prepare custom variables for the Unfold admin index template.
    """
    total_users = User.objects.filter(is_active=True).count()
    total_projects = Project.objects.count()
    active_projects = Project.objects.filter(status=ProjectStatusChoices.ACTIVE).count()
    
    # Calculate funds raised
    total_raised = Project.objects.aggregate(total=Sum('raised_amount'))['total'] or 0
    
    # Simple chart data for projects over last 6 months (mocked trend)
    months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    current_month = now().month
    
    # Get last 6 months labels
    chart_labels = []
    for i in range(5, -1, -1):
        m = (current_month - i - 1) % 12
        chart_labels.append(months[m])
        
    # Fetch recent data for tables
    recent_projects = list(Project.objects.order_by('-created_at')[:5].values('id', 'title', 'status', 'raised_amount', 'created_at'))
    
    # Format the dates
    for p in recent_projects:
        p['created_at_str'] = p['created_at'].strftime("%Y-%m-%d")
        
    sponsors_count = User.objects.filter(role="SPONSOR").count()
    investors_count = User.objects.filter(role="INVESTOR").count()

    # Build chart JSON data
    import json
    chart_data = json.dumps({
        "type": "line",
        "data": {
            "labels": chart_labels,
            "datasets": [
                {
                    "label": "New Investments & Projects",
                    "data": [2, 5, 3, 8, 12, max(active_projects, 14)],
                    "borderColor": "#3b82f6", # Tailwind blue-500
                    "backgroundColor": "rgba(59, 130, 246, 0.2)",
                    "fill": True,
                    "tension": 0.4
                }
            ]
        },
        "options": {
            "responsive": True,
            "maintainAspectRatio": False,
            "plugins": {
                "legend": {"display": False}
            },
            "scales": {
                "y": {"beginAtZero": True}
            }
        }
    })
    
    doughnut_data = json.dumps({
        "type": "doughnut",
        "data": {
            "labels": ["Sponsors", "Investors"],
            "datasets": [{
                "data": [max(sponsors_count, 1), max(investors_count, 1)],
                "backgroundColor": ["#3b82f6", "#93c5fd"],
                "borderWidth": 0
            }]
        },
        "options": {
            "responsive": True,
            "maintainAspectRatio": False,
            "cutout": "75%",
            "plugins": {
                "legend": {"position": "bottom"}
            }
        }
    })
        
    context.update({
        "kpi": [
            {"title": "Active Users", "metric": f"{total_users:,}", "footer": "Registered investors & sponsors"},
            {"title": "Total Projects", "metric": f"{total_projects:,}", "footer": f"{active_projects} currently active"},
            {"title": "Total Funds Raised", "metric": f"${total_raised:,.2f}", "footer": "Across all projects"},
        ],
        "chart_json": chart_data,
        "doughnut_json": doughnut_data,
        "recent_projects": recent_projects
    })
    return context
