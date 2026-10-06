# Project Termination & Filtering API Specification

This document details the backend requirements for the **Project Termination Flow**, **Terminated Projects Tab Filtering**, and **Automated Investor Notifications** in DiasporaVest / Braintech.

---

## 1. Project Termination Endpoint

### `POST /api/v1/projects/<id>/terminate/`
Allows a sponsor to officially terminate their own project. This is a soft termination (status update), not a destructive database delete.

#### Headers
| Header | Value | Description |
|---|---|---|
| `Authorization` | `Bearer <access_token>` | Sponsor's JWT token |
| `Content-Type` | `application/json` | |

#### Request Body
```json
{
  "reason": "Municipal zoning permits were denied for the tech hub facility."
}
```

| Field | Type | Required | Description |
|---|---|---|---|
| `reason` | `string` | ✅ Yes | Detailed reason for termination (Minimum 10 characters, maximum 1000 characters). |

---

### Response Specifications

#### Success (`200 OK`)
```json
{
  "status": "success",
  "message": "Project has been terminated successfully.",
  "data": {
    "id": 3,
    "title": "Downtown Tech Hub",
    "status": "TERMINATED",
    "terminated_at": "2026-10-06T12:00:00Z",
    "termination_reason": "Municipal zoning permits were denied for the tech hub facility."
  }
}
```

#### Error Responses

| Status Code | Scenario | Response Body |
|---|---|---|
| `400 Bad Request` | Reason missing or < 10 characters | `{"error": "Termination reason is required and must be at least 10 characters."}` |
| `400 Bad Request` | Project is already terminated | `{"error": "This project is already terminated."}` |
| `401 Unauthorized` | Missing / invalid token | `{"detail": "Authentication credentials were not provided."}` |
| `403 Forbidden` | User is not the owner (sponsor) | `{"error": "You do not have permission to terminate this project."}` |
| `404 Not Found` | Project ID does not exist | `{"error": "Project not found."}` |

---

## 2. Terminated Projects Tab & Filtering

The sponsor mobile app contains a dedicated tab bar (`ProjectsTabBar` in `all_projects` view) with four tabs:
1. **All Projects**
2. **Active Projects** (`status = ACTIVE` or `FUNDING_ACTIVE`)
3. **Completed** (`status = COMPLETED` or `FUNDED`)
4. **Terminated** (`status = TERMINATED` or `CANCELLED`)

### Endpoint: `GET /api/v1/projects/sponsor/`

The backend should support filtering by status via query parameter:

```http
GET /api/v1/projects/sponsor/?status=TERMINATED
```

#### Supported Query Parameters
| Parameter | Possible Values | Behavior |
|---|---|---|
| `status` | `all` (default) | Returns all projects owned by the sponsor (active, completed, terminated). |
| `status` | `active` | Returns only active/funding projects (`ACTIVE`, `FUNDING_ACTIVE`). |
| `status` | `completed` | Returns only successfully funded/completed projects (`COMPLETED`). |
| `status` | `terminated` | Returns only terminated projects (`TERMINATED`, `CANCELLED`). |

> **Note for Django backend**: If `status` parameter is omitted, return ALL projects owned by the sponsor with their appropriate `"status"` string (`"ACTIVE"`, `"COMPLETED"`, `"TERMINATED"`). The mobile app can then either display the unified list or query each tab specifically.

---

## 3. Investor Push & In-App Notification Logic

When a project is terminated via `POST /api/v1/projects/<id>/terminate/`, the backend **must immediately trigger notifications** to all impacted investors:

### Who receives the notification?
All investors who:
1. Have signed an NDA for this project (`NdaSignature.objects.filter(project=project)`), **OR**
2. Have submitted a Collaboration Request for this project (`CollaborationRequest.objects.filter(project=project)`).

### Notification Actions
1. **In-App Notification**:
   Insert a new notification record in the `notifications` table:
   - `recipient`: `investor.user`
   - `title`: `Project Terminated`
   - `message`: `"${project.title}" has been terminated by the sponsor. Reason: ${reason}`
   - `type`: `PROJECT_TERMINATED`
   - `data`: `{"project_id": project.id, "reason": reason}`
   - `created_at`: `now()`

2. **Push Notification (FCM / Firebase Cloud Messaging)**:
   Dispatch a push notification to each investor's registered device tokens:
   - `title`: `⚠️ Project Terminated: ${project.title}`
   - `body`: `The sponsor has terminated this project: ${reason.truncate(100)}`
   - `data`: `{"type": "PROJECT_TERMINATED", "project_id": str(project.id)}`

---

## 4. Business Logic & Django Reference Implementation

```python
# models.py
class Project(models.Model):
    STATUS_CHOICES = [
        ('DRAFT', 'Draft'),
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
        ('TERMINATED', 'Terminated'),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE')
    termination_reason = models.TextField(null=True, blank=True)
    terminated_at = models.DateTimeField(null=True, blank=True)
    # ... other existing fields

# views.py
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def terminate_project(request, pk):
    try:
        project = Project.objects.get(pk=pk)
    except Project.DoesNotExist:
        return Response({"error": "Project not found."}, status=status.HTTP_404_NOT_FOUND)

    # 1. Permission check
    if project.sponsor != request.user.sponsor_profile:
        return Response({"error": "You do not have permission to terminate this project."}, status=status.HTTP_403_FORBIDDEN)

    # 2. Status check
    if project.status == 'TERMINATED':
        return Response({"error": "This project is already terminated."}, status=status.HTTP_400_BAD_REQUEST)

    # 3. Reason validation
    reason = request.data.get('reason', '').strip()
    if len(reason) < 10:
        return Response({"error": "Termination reason is required and must be at least 10 characters."}, status=status.HTTP_400_BAD_REQUEST)

    # 4. Soft terminate
    project.status = 'TERMINATED'
    project.termination_reason = reason
    project.terminated_at = timezone.now()
    project.save(update_fields=['status', 'termination_reason', 'terminated_at'])

    # 5. Notify investors asynchronously
    notify_project_investors_of_termination.delay(project.id, reason)

    return Response({
        "status": "success",
        "message": "Project has been terminated successfully.",
        "data": {
            "id": project.id,
            "title": project.title,
            "status": project.status,
            "terminated_at": project.terminated_at,
            "termination_reason": project.termination_reason,
        }
    }, status=status.HTTP_200_OK)
```

---

## 5. Security & Post-Termination Restrictions
Once `project.status == 'TERMINATED'`:
- Investors **cannot** submit new collaboration requests (return `400: Project is no longer accepting requests`).
- Investors **cannot** sign NDAs for this project.
- Active chat conversations remain readable for historical/legal compliance, but new messages should indicate the project has concluded.
