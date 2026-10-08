# AI Chat (Investment Copilot) API Specification

Backend API contract for `AiChatView` (`lib/views/ai_chat/`).

---

## Base Configuration

- **Base Path:** `/api/v1/ai/chat`
- **Auth:** Bearer Token (`Authorization: Bearer <access_token>`)
- **Content-Type:** `application/json`

---

## 1. Get Initial State & Quick Prompts

Fetch default welcome message and initial quick prompt chips on screen load.

- **Method:** `GET`
- **Endpoint:** `/api/v1/ai/chat/initial/`
- **Headers:**
  ```http
  Authorization: Bearer <access_token>
  ```

### Response `200 OK`
```json
{
  "status": "success",
  "data": {
    "conversation_id": "c9a4b8e2-4f3d-4c8a-9e12-8d7e6f5a4b3c",
    "welcome_message": {
      "id": "msg_welcome",
      "text": "Hello! I am your AI Investment Copilot. How can I help you optimize your portfolio or projects today?",
      "is_user": false,
      "created_at": "2026-10-08T10:00:00.000Z",
      "suggestions": [
        "Explore Top Projects",
        "Draft New Proposal",
        "Market Analytics"
      ]
    },
    "quick_prompts": [
      "Analyze high-yield real estate projects",
      "How do I create a new funding request?",
      "Calculate estimated ROI for Tech Hub",
      "What are current market trends?"
    ]
  }
}
```

---

## 2. Send Message to AI Copilot

Send user query and receive AI answer with dynamic follow-up suggestions.

- **Method:** `POST`
- **Endpoint:** `/api/v1/ai/chat/conversations/{conversation_id}/messages/`
- **Headers:**
  ```http
  Authorization: Bearer <access_token>
  Content-Type: application/json
  ```

### Request Payload
```json
{
  "content": "Analyze high-yield real estate projects",
  "context": {
    "current_screen": "ai_chat",
    "role": "investor"
  }
}
```

### Request Fields
| Field | Type | Required | Description |
|---|---|---|---|
| `content` | `string` | **Yes** | User input text / selected chip prompt. |
| `context` | `object` | No | Extra metadata (user role, active project ID, filters). |

### Response `200 OK`
```json
{
  "status": "success",
  "data": {
    "user_message": {
      "id": "msg_usr_1728381234",
      "text": "Analyze high-yield real estate projects",
      "is_user": true,
      "created_at": "2026-10-08T10:05:00.000Z"
    },
    "ai_reply": {
      "id": "msg_ai_1728381235",
      "text": "Downtown Tech Hub currently offers a 18% target ROI with a minimum investment of $1,000. Located in Prime Tech District with 75% funded status.",
      "is_user": false,
      "created_at": "2026-10-08T10:05:02.000Z",
      "suggestions": [
        "Show Financial Breakdown",
        "Connect with Sponsor",
        "View Documents"
      ]
    },
    "updated_quick_prompts": [
      "Calculate ROI for Downtown Tech Hub",
      "Check sponsor verification status",
      "Compare with other Real Estate deals"
    ]
  }
}
```

---

## 3. Get Conversation History

Fetch existing message history when re-opening chat.

- **Method:** `GET`
- **Endpoint:** `/api/v1/ai/chat/conversations/{conversation_id}/messages/`
- **Query Params:**
  - `page` (optional, default: `1`)
  - `page_size` (optional, default: `30`)

### Response `200 OK`
```json
{
  "status": "success",
  "data": {
    "conversation_id": "c9a4b8e2-4f3d-4c8a-9e12-8d7e6f5a4b3c",
    "count": 4,
    "next": null,
    "previous": null,
    "messages": [
      {
        "id": "msg_welcome",
        "text": "Hello! I am your AI Investment Copilot. How can I help you optimize your portfolio or projects today?",
        "is_user": false,
        "created_at": "2026-10-08T09:00:00.000Z",
        "suggestions": [
          "Explore Top Projects",
          "Draft New Proposal",
          "Market Analytics"
        ]
      },
      {
        "id": "msg_usr_1001",
        "text": "What is the average ROI?",
        "is_user": true,
        "created_at": "2026-10-08T09:01:10.000Z",
        "suggestions": null
      },
      {
        "id": "msg_ai_1002",
        "text": "Based on historical performance, average returns across tech & energy portfolios range from 12% to 25% annually.",
        "is_user": false,
        "created_at": "2026-10-08T09:01:12.000Z",
        "suggestions": [
          "Show Top Performers",
          "Risk Assessment"
        ]
      }
    ]
  }
}
```

---

## 4. Clear / Reset Chat Session

Clear message thread and reset conversation state (triggered by AppBar clear button).

- **Method:** `DELETE` (or `POST`)
- **Endpoint:** `/api/v1/ai/chat/conversations/{conversation_id}/clear/`
- **Headers:**
  ```http
  Authorization: Bearer <access_token>
  ```

### Response `200 OK`
```json
{
  "status": "success",
  "message": "Chat history cleared successfully.",
  "data": {
    "new_conversation_id": "e81d4c72-91f0-4a8d-b312-32a188f6c91e",
    "welcome_message": {
      "id": "msg_welcome",
      "text": "Hello! I am your AI Investment Copilot. How can I help you optimize your portfolio or projects today?",
      "is_user": false,
      "created_at": "2026-10-08T10:10:00.000Z",
      "suggestions": [
        "Explore Top Projects",
        "Draft New Proposal",
        "Market Analytics"
      ]
    }
  }
}
```

---

## 5. Error Responses

Standard application error schema across all endpoints.

### 400 Bad Request
```json
{
  "status": "error",
  "message": "Content cannot be empty."
}
```

### 401 Unauthorized
```json
{
  "status": "error",
  "message": "Authentication credentials were not provided or invalid."
}
```

### 429 Rate Limit / Quota Exceeded
```json
{
  "status": "error",
  "message": "AI request quota exceeded. Please wait before asking another query.",
  "retry_after": 15
}
```

### 500 LLM Gateway Error
```json
{
  "status": "error",
  "message": "AI Copilot service temporarily unavailable. Please try again."
}
```

---

## 6. Dart Model Field Mapping

| Backend JSON Key | Dart Model Field | Dart Type | Nullable |
|---|---|---|---|
| `id` | `id` | `String` | No |
| `text` / `content` | `text` | `String` | No |
| `is_user` | `isUser` | `bool` | No |
| `created_at` / `timestamp` | `timestamp` | `DateTime` | No |
| `suggestions` | `suggestions` | `List<String>?` | Yes |
| `quick_prompts` | `quickPrompts` | `List<String>` | No |
