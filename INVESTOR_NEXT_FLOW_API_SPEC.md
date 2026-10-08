# Investor Next Flow & Lifecycle Backend API Specification

This document specifies the **Next Flow (Stage 2 - Post-Collaboration Request Submission & Deal Lifecycle)** APIs and payloads for backend development.

---

## 1. Lifecycle Overview

```
[Investor Submits Request] 
         │
         ▼
[Sponsor Receives Request] (GET /api/v1/projects/sponsor/requests/)
         │
    ┌────┴────────────────────────┐
    ▼                             ▼
[Approve]                     [Reject]
(POST .../approve/)           (POST .../reject/)
    │
    ▼
[Direct / Syndicate Chat Created] (POST /api/v1/notifications/chat/conversations/start/)
    │
    ▼
[Investor Wires Capital]
    │
    ▼
[Sponsor Marks Fund Received] (POST .../fund-received/)
    │
    ▼
[Sponsor Confirms Investors in Syndicate] (POST .../confirm-investors/)
    │
    ▼
[Deal Active in Investor History] (GET /api/v1/investor/investments/)
```

---

## 2. API Endpoints & Contracts

### 2.1. Sponsor Receives & Lists Incoming Collaboration Requests
- **Method:** `GET`
- **Endpoint:** `/api/v1/projects/sponsor/requests/`
- **Query Params:** `project_id` (optional filter), `status=PENDING`
- **Auth:** Bearer Token (Sponsor)

#### Response `200 OK`
```json
{
  "status": "success",
  "data": {
    "count": 2,
    "results": [
      {
        "id": "req_8812",
        "project_id": "proj_9876",
        "project_title": "Downtown Tech Hub",
        "investor": {
          "id": "usr_inv_44",
          "name": "Sarah Connor",
          "avatar_url": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?q=80&w=150",
          "company": "Venture Horizons",
          "is_verified": true
        },
        "proposed_budget": 250000,
        "message": "We would like to join this seed round as a strategic investor.",
        "status": "PENDING",
        "created_at": "2026-10-08T10:30:00.000Z"
      }
    ]
  }
}
```

---

### 2.2. Sponsor Approves Collaboration Request
- **Method:** `POST`
- **Endpoint:** `/api/v1/projects/sponsor/requests/{request_id}/approve/`
- **Auth:** Bearer Token (Sponsor)
- **Side Effect:** Automatically starts/provisions a direct conversation between Sponsor and Investor.

#### Response `200 OK`
```json
{
  "status": "success",
  "message": "Collaboration request approved. Deal room conversation initiated.",
  "data": {
    "request_id": "req_8812",
    "status": "APPROVED",
    "conversation_id": "conv_9901",
    "updated_at": "2026-10-08T10:45:00.000Z"
  }
}
```

---

### 2.3. Sponsor Rejects Collaboration Request
- **Method:** `POST`
- **Endpoint:** `/api/v1/projects/sponsor/requests/{request_id}/reject/`
- **Auth:** Bearer Token (Sponsor)

#### Request Body
```json
{
  "reason": "Target round allocation is currently full."
}
```

#### Response `200 OK`
```json
{
  "status": "success",
  "message": "Collaboration request rejected.",
  "data": {
    "request_id": "req_8812",
    "status": "REJECTED"
  }
}
```

---

### 2.4. Sponsor Marks Funds Received (Capital Deployed)
- **Method:** `POST`
- **Endpoint:** `/api/v1/projects/sponsor/requests/{request_id}/fund-received/`
- **Auth:** Bearer Token (Sponsor)

#### Request Body
```json
{
  "received_amount": 250000,
  "payment_reference": "WIRE-20261008-9901",
  "received_at": "2026-10-08T11:00:00.000Z"
}
```

#### Response `200 OK`
```json
{
  "status": "success",
  "message": "Funds recorded successfully.",
  "data": {
    "request_id": "req_8812",
    "status": "FUNDED",
    "amount": 250000
  }
}
```

---

### 2.5. Sponsor Confirms Investors in Deal Syndicate
- **Method:** `POST`
- **Endpoint:** `/api/v1/projects/{project_id}/confirm-investors/`
- **Auth:** Bearer Token (Sponsor)

#### Request Body
```json
{
  "confirmed_investor_ids": ["usr_inv_44"],
  "closing_date": "2026-10-08"
}
```

#### Response `200 OK`
```json
{
  "status": "success",
  "message": "Investors confirmed into syndicate. Active investment records generated for all participants.",
  "data": {
    "project_id": "proj_9876",
    "total_confirmed_investors": 1,
    "project_status": "ACTIVE_SYNDICATE"
  }
}
```
