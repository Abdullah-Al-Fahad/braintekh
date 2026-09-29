# Sponsor & Collaboration Requests API Specification

This document outlines the API contracts and required response fields for the **Sponsor Dashboard**, **All Projects**, and **Collaboration Requests** modules in the Flutter mobile application.

---

## 1. Sponsor Projects API

### `GET /api/v1/projects/sponsor/`
Fetches all projects created by the authenticated sponsor.

- **Auth Required**: Yes (`Bearer <token>`)
- **Pagination**: Paginated response (`data` or `results`)

#### Expected Response Body
```json
{
  "success": true,
  "count": 3,
  "total_pages": 1,
  "current_page": 1,
  "data": [
    {
      "id": 1,
      "title": "Downtown Tech Hub",
      "short_description": "State-of-the-art tech hub in downtown Austin.",
      "description": "Comprehensive description of commercial tech real estate...",
      "status": "ACTIVE",
      "funding_goal": "5000000.00",
      "raised_amount": "1200000.00",
      "progress": 0.24,
      "category": {
        "id": 2,
        "name": "Technology"
      },
      "industry": "Commercial Real Estate",
      "category_ids": [2],
      "cover_image": "https://clubby-andy-irksomely.ngrok-free.dev/media/projects/cover_1.jpg",
      "target_roi": "18.5",
      "minimum_investment": "25000.00",
      "created_at": "2026-09-27T10:04:37.890039Z"
    }
  ]
}
```

#### Field Specifications & Frontend Requirements

| Field | Type | Required by UI | Backend Action Needed |
| :--- | :--- | :---: | :--- |
| `id` | `int` / `string` | **Yes** | Project identifier used for detail routing. |
| `title` | `string` | **Yes** | Main project title. |
| `short_description` | `string` | **Yes** | 1-2 sentence summary displayed on card. Fallback to `description`. |
| `status` | `string` | **Yes** | Enum: `"ACTIVE"`, `"COMPLETED"`, `"TERMINATED"`, `"DRAFT"`. Used for tab categorization. |
| `funding_goal` | `string` / `number` | **Yes** | Target funding goal (e.g., `5000000.00`). |
| `raised_amount` | `string` / `number` | **CRITICAL** | **Currently missing in static model.** Must be aggregated sum of approved/funded contributions. |
| `progress` | `float` (0.0 - 1.0) | Optional | Ratio of `raised_amount / funding_goal`. (Frontend can compute if `raised_amount` is provided). |
| `category` | `object` / `string` | **Yes** | Expanded category object (`{"id": 1, "name": "Tech"}`) or name string. Do not send only numeric IDs. |
| `cover_image` | `string?` | Optional | Absolute or relative media URL to banner image. |
| `created_at` | `ISO 8601 string` | **Yes** | Used to sort projects descending (most recent first on dashboard). |

---

## 2. Collaboration Requests API

### `GET /api/v1/projects/sponsor/requests/`
Fetches all investor collaboration / NDA requests sent to this sponsor.

- **Auth Required**: Yes (`Bearer <token>`)

#### Current API Response Payload
```json
{
  "success": true,
  "links": {
    "next": null,
    "previous": null
  },
  "count": 3,
  "total_pages": 1,
  "current_page": 1,
  "data": [
    {
      "id": 1,
      "project": {
        "id": 2,
        "title": "Dummy Project 2 by ismail"
      },
      "investor": {
        "id": 8,
        "name": "Investor 1 Fake",
        "investor_type": "INDIVIDUAL",
        "photo": null
      },
      "proposed_budget": "75000.00",
      "proposal_text": "I am very interested in funding Dummy Project 2 by ismail.",
      "status": "PENDING",
      "nda_signed": false,
      "nda_digital_signature": "",
      "nda_signature_image": null,
      "created_at": "2026-09-27T10:04:37.890039Z"
    }
  ]
}
```

#### Field Specifications

| Field | Type | Description |
| :--- | :--- | :--- |
| `id` | `int` | Unique request ID. |
| `project.id` | `int` | ID of the target project. |
| `project.title` | `string` | Title of the target project. |
| `investor.id` | `int` | Investor user ID. |
| `investor.name` | `string` | Display name of the investor. |
| `investor.investor_type` | `string` | `"INDIVIDUAL"`, `"VENTURE_CAPITAL"`, `"ANGEL"`, `"PRIVATE_EQUITY"`. |
| `investor.photo` | `string?` | Relative or absolute profile photo URL (or `null`). |
| `proposed_budget` | `string` | Proposed allocation amount (e.g., `"75000.00"`). |
| `proposal_text` | `string` | Message or note from the investor. |
| `status` | `string` | `"PENDING"`, `"APPROVED"`, `"CONFIRMED"`, `"REJECTED"`. |
| `nda_signed` | `boolean` | `true` if NDA has been digitally signed by the investor. |
| `created_at` | `ISO 8601 string` | Timestamp used for sorting the most recent request on the dashboard. |

---

## 3. Recommended Request Action Endpoints

To replace client-side state manipulation with persistent backend mutations, implement these action endpoints:

### A. Approve Collaboration Request
- **Endpoint**: `POST /api/v1/projects/sponsor/requests/{id}/approve/`
- **Action**: Transitions status from `PENDING` to `APPROVED`.
- **Response**:
```json
{
  "success": true,
  "message": "Request approved successfully",
  "data": {
    "id": 1,
    "status": "APPROVED"
  }
}
```

### B. Reject Collaboration Request
- **Endpoint**: `POST /api/v1/projects/sponsor/requests/{id}/reject/`
- **Action**: Transitions status from `PENDING` to `REJECTED`.
- **Response**:
```json
{
  "success": true,
  "message": "Request rejected",
  "data": {
    "id": 1,
    "status": "REJECTED"
  }
}
```

### C. Mark Fund Received
- **Endpoint**: `POST /api/v1/projects/sponsor/requests/{id}/fund-received/`
- **Action**: Confirms escrow or funding receipt (`status = "RECEIVED"` or `"CONFIRMED"`).
- **Response**:
```json
{
  "success": true,
  "message": "Fund marked as received",
  "data": {
    "id": 1,
    "status": "RECEIVED"
  }
}
```

---

## 4. Key Takeaways for Backend Developer
1. **Include `raised_amount`** in `GET /api/v1/projects/sponsor/` by calculating the sum of funded contributions.
2. **Expand `category`** name in project responses instead of only sending `category_ids: [1, 2]`.
3. **Keep `created_at` timestamps** on both endpoints so frontend can display the single most recent item on the dashboard.
