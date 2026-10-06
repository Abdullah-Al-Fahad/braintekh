# Group Chat App Bar & Management API Specification

This specification details all backend REST API endpoints, Role-Based Access Control (RBAC) permissions, database schema requirements, and WebSocket events triggered by the actions available in the **Group Chat App Bar** (`GroupChatAppBar`).

---

## 1. Role-Based Access Control (RBAC) Matrix

| Feature / Action | Popup Menu Key | Project Creator (Sponsor Owner) | Investor / Participant | Backend Guard |
| :--- | :--- | :---: | :---: | :--- |
| **View Group Info & Member Count** | Header UI | ✅ Allowed | ✅ Allowed | Caller must be an active participant |
| **Confirm Investor(s)** | `confirm_investor` | ✅ **Allowed** | ❌ **403 Forbidden** | `project.created_by_id == request.user.id` |
| **Remove Participant** | `remove_participant` | ✅ **Allowed** | ❌ **403 Forbidden** | `project.created_by_id == request.user.id` |
| **Report Group Chat** | `report` | ✅ Allowed | ✅ Allowed | Any active group member |
| **Leave Group Chat** | `leave` | ❌ **400 Bad Request** *(Owners cannot leave)* | ✅ **Allowed** | Inactive for project creator |

> [!IMPORTANT]
> **Owner-Only Security Constraint**:
> Both **"Confirm Investors"** and **"Remove Participant"** MUST be strictly protected on the backend. Never rely solely on frontend hiding. If an Investor or unauthorized user sends a request to these endpoints, the backend MUST respond with:
> ```json
> {
>   "status": "error",
>   "code": "PERMISSION_DENIED",
>   "message": "Only the project sponsor who created this project can perform this action."
> }
> ```

---

## 2. Endpoints Specification

All endpoints require:
`Authorization: Bearer <access_token>`  
`Content-Type: application/json`

---

### 2.1 Fetch Group Header & Participant Metadata
Returns metadata for the top bar: project title, active member count, caller ownership flag, and list of participants for the avatar stack.

- **Endpoint**: `GET /api/v1/notifications/chat/conversations/{conversation_id}/header/`
- **Response (`200 OK`)**:
```json
{
  "status": "success",
  "data": {
    "conversation_id": 1,
    "project_id": 3,
    "project_title": "Downtown Tech Hub",
    "is_owner": true,
    "active_member_count": 5,
    "participants": [
      {
        "user_id": 14,
        "name": "Sarah Connor",
        "role": "Sponsor",
        "is_owner": true,
        "avatar_url": "https://storage.example.com/avatars/sarah.jpg",
        "initials": "SC"
      },
      {
        "user_id": 8,
        "name": "David Chen",
        "role": "Investor",
        "is_owner": false,
        "avatar_url": null,
        "initials": "DC"
      },
      {
        "user_id": 22,
        "name": "Elena Rostova",
        "role": "Investor",
        "is_owner": false,
        "avatar_url": "https://storage.example.com/avatars/elena.jpg",
        "initials": "ER"
      }
    ]
  }
}
```

---

### 2.2 Confirm Investor (`confirm_investor`)
Executed by the project sponsor when officially locking in one or more investors from the group into project funding.

- **Endpoint**: `POST /api/v1/projects/{project_id}/confirm-investors/`  
  *(Alternative alias: `POST /api/v1/notifications/chat/conversations/{conversation_id}/confirm-investors/`)*
- **Permission**: Project Creator Sponsor only (`project.created_by_id == request.user.id`).
- **Request Body**:
```json
{
  "conversation_id": 1,
  "investors": [
    {
      "investor_id": 8,
      "name": "David Chen",
      "confirmed_amount": 50000.00,
      "share_percentage": 5.0,
      "notes": "Angel round commitment verified via NDA & proof of funds"
    },
    {
      "investor_id": 22,
      "name": "Elena Rostova",
      "confirmed_amount": 75000.00,
      "share_percentage": 7.5,
      "notes": "Co-lead participation"
    }
  ]
}
```

- **Backend Business Logic**:
  1. Verify caller owns `project_id`. If not, return `403 Forbidden`.
  2. Create or update records in `ProjectContribution` / `InvestmentRecord` with `status = "CONFIRMED"`.
  3. Increment project stats:
     - `project.total_raised += sum(confirmed_amounts)`
     - `project.active_investors_count += new_investors_count`
  4. Automatically create and append a **System Chat Message** to the group conversation:
     - `sender_id`: `null`
     - `message_type`: `"system"`
     - `text`: `"🎉 Confirmed investors: David Chen ($50,000) and Elena Rostova ($75,000) have officially joined the project!"`
  5. Broadcast real-time WebSocket event `investor_confirmed` to the chat room.

- **Response (`200 OK`)**:
```json
{
  "status": "success",
  "message": "2 investors confirmed successfully.",
  "data": {
    "project_id": 3,
    "total_raised": "$125,000.00",
    "confirmed_investors_count": 2,
    "system_message": {
      "id": 1054,
      "conversation_id": 1,
      "sender_id": null,
      "sender_role": "System",
      "message_type": "system",
      "text": "🎉 Confirmed investors: David Chen ($50,000) and Elena Rostova ($75,000) have officially joined the project!",
      "created_at": "2026-10-05T16:30:00Z"
    }
  }
}
```

- **Error Response (Non-owner attempt - `403 Forbidden`)**:
```json
{
  "status": "error",
  "code": "FORBIDDEN_ACTION",
  "message": "Only the project sponsor who created this project can confirm investors."
}
```

---

### 2.3 Remove Participant (`remove_participant`)
Executed by the project sponsor to remove an investor or disruptive member from the group chat.

- **Endpoint**: `POST /api/v1/notifications/chat/conversations/{conversation_id}/remove-participant/`  
  *(Alternative HTTP REST: `DELETE /api/v1/notifications/chat/conversations/{conversation_id}/participants/{user_id}/`)*
- **Permission**: Project Creator Sponsor only (`project.created_by_id == request.user.id`).
- **Request Body**:
```json
{
  "target_user_id": 22,
  "reason": "Requested withdrawal from the opportunity."
}
```

- **Backend Business Logic**:
  1. Verify caller owns the project linked to `conversation_id`.
  2. Prevent owner from removing themselves (`target_user_id == request.user.id` -> `400 Bad Request`).
  3. Mark `ConversationParticipant.is_active = false` (or delete membership record).
  4. Post an automated system message:
     - `message_type`: `"system"`
     - `text`: `"Elena Rostova was removed from the group by the owner."`
  5. Broadcast WebSocket event `participant_removed` to:
     - Room members (updates member count & removes user from active list).
     - Target user's socket (triggers auto-exit / disables chat input on their device).

- **Response (`200 OK`)**:
```json
{
  "status": "success",
  "message": "Participant removed from group chat.",
  "data": {
    "conversation_id": 1,
    "removed_user_id": 22,
    "remaining_member_count": 4,
    "system_message_id": 1055
  }
}
```

- **Error Response (Self-Removal Attempt - `400 Bad Request`)**:
```json
{
  "status": "error",
  "code": "INVALID_TARGET",
  "message": "Project creator cannot be removed from their own project group chat."
}
```

---

### 2.4 Report Group Chat (`report`)
Enables any participant (sponsor or investor) to submit a report for spam, misconduct, or fraudulent activities.

- **Endpoint**: `POST /api/v1/notifications/chat/conversations/{conversation_id}/report/`
- **Permission**: Any active participant of the conversation.
- **Request Body**:
```json
{
  "reason": "SUSPICIOUS_ACTIVITY",
  "description": "Unregistered solicitation of external off-platform tokens.",
  "flagged_message_ids": [1042, 1045]
}
```
*Enum for `reason`: `"SPAM"`, `"HARASSMENT"`, `"SUSPICIOUS_ACTIVITY"`, `"FRAUD"`, `"OTHER"`.*

- **Response (`201 Created`)**:
```json
{
  "status": "success",
  "message": "Report submitted successfully. Our compliance team will review this chat.",
  "report_id": "REP-94821"
}
```

---

### 2.5 Leave Group Chat (`leave`)
Allows investors and participants to leave a group chat they no longer wish to follow.

- **Endpoint**: `POST /api/v1/notifications/chat/conversations/{conversation_id}/leave/`
- **Permission**: Regular participants only.
- **Request Body**: `{}`

- **Backend Business Logic**:
  1. If `project.created_by_id == request.user.id`, **REJECT** with `400 Bad Request`:
     *"The project creator cannot leave the project group chat. You can archive the project if you wish to close it."*
  2. Mark caller's `ConversationParticipant.is_active = false`.
  3. Create automated system message:
     - `text`: `"[User Name] left the group."`
  4. Broadcast `participant_left` event via WebSocket.

- **Response (`200 OK`)**:
```json
{
  "status": "success",
  "message": "You have left the group chat.",
  "data": {
    "conversation_id": 1,
    "is_active": false
  }
}
```

- **Error Response (Owner trying to leave - `400 Bad Request`)**:
```json
{
  "status": "error",
  "code": "OWNER_CANNOT_LEAVE",
  "message": "Project owners cannot leave their project group chat."
}
```

---

## 3. Real-Time WebSocket Notifications

When actions occur via the app bar, backend broadcasts events over `ws/chat/{conversation_id}/`:

### 3.1 Event: `investor_confirmed`
```json
{
  "type": "investor_confirmed",
  "conversation_id": 1,
  "project_id": 3,
  "confirmed_investors": [
    {
      "investor_id": 8,
      "name": "David Chen",
      "amount": "$50,000.00"
    }
  ],
  "system_message": {
    "id": 1054,
    "text": "🎉 Confirmed investor: David Chen ($50,000.00) has joined the project!",
    "created_at": "2026-10-05T16:30:00Z"
  }
}
```

### 3.2 Event: `participant_removed`
```json
{
  "type": "participant_removed",
  "conversation_id": 1,
  "user_id": 22,
  "user_name": "Elena Rostova",
  "new_member_count": 4,
  "system_message": {
    "id": 1055,
    "text": "Elena Rostova was removed from the group by the owner.",
    "created_at": "2026-10-05T16:31:00Z"
  }
}
```

### 3.3 Event: `participant_left`
```json
{
  "type": "participant_left",
  "conversation_id": 1,
  "user_id": 15,
  "user_name": "Marcus Vance",
  "new_member_count": 3,
  "system_message": {
    "id": 1056,
    "text": "Marcus Vance left the group.",
    "created_at": "2026-10-05T16:35:00Z"
  }
}
```

---

## 4. Frontend UI Alignment (`GroupChatAppBar`)

In `group_chat_app_bar.dart`, the popup menu conditionally displays items based on `isOwner`:
- If `isOwner == true`: Displays **"Confirm Investors"**, **"Remove Participant (Owner)"**, and **"Report Group"**.
- If `isOwner == false`: Displays **"Report Group"** and **"Leave Group"**.

This guarantees non-sponsors never see owner administration tools in the UI, complemented by strict backend validation.
