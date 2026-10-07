# AI Project Creation — Backend Requirements

**From**: Frontend (Flutter)
**To**: Backend Dev
**Feature**: "Create with AI" — Sponsor creates a project via AI chat (Damini Advisor)
**Date**: October 7, 2026

---

## What I've Built (Frontend Side)

I have a **fully working chat UI** where sponsors can create projects by chatting with an AI assistant called "Damini Advisor". Right now **everything is hardcoded** — the AI responses, step transitions, and the generated project blueprint are all static dummy data on the frontend.

I need **real backend APIs** to power this feature.

### My Current File Structure

```
lib/views/sponsor/create_project/
├── controllers/
│   ├── project_creation_ai_provider.dart   ← ⚠️ All AI logic hardcoded here
│   ├── create_project_provider.dart        ← Submits final project (working)
│   └── project_draft_provider.dart         ← Local draft caching
├── models/
│   ├── project_draft_model.dart            ← Draft model (AI generates this)
│   └── create_project_models.dart          ← Final submit model (FormData)
├── repositories/
│   ├── create_project_repository.dart      ← POST /api/v1/projects/sponsor/ (working)
│   └── project_draft_repository.dart       ← SharedPreferences cache
├── screens/
│   ├── project_creation_ai_chat_view.dart  ← Chat UI (working)
│   └── create_project_view.dart            ← Project form (working)
└── widgets/
    ├── damini_ai_interactive_header.dart   ← Step progress header
    ├── damini_blueprint_card.dart          ← Shows generated draft
    ├── damini_interactive_chips.dart       ← Suggestion chips
    └── ...other form widgets
```

### How the Flow Works Right Now

```
1. Sponsor taps "Create with AI" button on home
2. Opens chat screen with welcome message
3. AI asks 3 questions one by one:
   - Step 1: "What industry?" → user picks/types
   - Step 2: "Describe your business idea" → user types
   - Step 3: "What's your funding goal?" → user picks/types
4. AI generates a "Project Blueprint" card
5. User taps "Apply Blueprint" → navigates to project form with all fields pre-filled
6. User reviews, edits if needed, taps Submit
7. Submit hits existing POST /api/v1/projects/sponsor/ (this part already works)
```

**Steps 2-4 are hardcoded. I need backend APIs for these.**

---

## What I Need From You

### 4 Endpoints

---

### ① Start Conversation

```
POST /api/v1/ai/projects/conversations/
Authorization: Bearer <token>
Content-Type: application/json
```

**Request** (body can be empty or):
```json
{
  "initial_context": "optional text"
}
```

**Response I expect** `201`:
```json
{
  "status": "success",
  "data": {
    "conversation_id": "conv_abc123",
    "step": "industry",
    "step_index": 1,
    "total_steps": 4,
    "step_title": "Select Industry",
    "message": {
      "id": "msg_001",
      "role": "assistant",
      "content": "Hi, I'm Damini Advisor. I can help you create a new project. To get started, what industry is your project in?",
      "timestamp": "2026-10-07T09:00:00Z",
      "suggestions": ["Technology", "Clean Energy", "Real Estate", "Healthcare", "Fintech"]
    }
  }
}
```

I use `step_index` and `total_steps` to show a progress bar. `step_title` displays as header text. `suggestions` become tappable chips below the chat.

---

### ② Send Message & Get AI Response

```
POST /api/v1/ai/projects/conversations/{conversation_id}/messages/
Authorization: Bearer <token>
Content-Type: application/json
```

**Request**:
```json
{
  "content": "Technology"
}
```

**Response for steps 1-3** `200` (no draft yet):
```json
{
  "status": "success",
  "data": {
    "step": "description",
    "step_index": 2,
    "total_steps": 4,
    "step_title": "Project Concept",
    "message": {
      "id": "msg_003",
      "role": "assistant",
      "content": "Great! You chose Technology. Now, could you provide a brief description of your business idea?",
      "timestamp": "2026-10-07T09:01:30Z",
      "suggestions": [
        "A renewable energy solar farm project",
        "A downtown tech hub",
        "An innovative healthcare app"
      ]
    },
    "extracted_data": {
      "industry": "Technology"
    },
    "draft": null
  }
}
```

**Response for final step** `200` (draft included):
```json
{
  "status": "success",
  "data": {
    "step": "done",
    "step_index": 4,
    "total_steps": 4,
    "step_title": "Blueprint Ready!",
    "message": {
      "id": "msg_007",
      "role": "assistant",
      "content": "I've generated a complete project blueprint based on our conversation. Review it below!",
      "timestamp": "2026-10-07T09:03:00Z",
      "suggestions": ["Apply to Project"]
    },
    "extracted_data": {
      "industry": "Technology",
      "description": "AI-powered supply chain platform",
      "funding_goal": "5000000"
    },
    "draft": {
      "id": "draft_xyz789",
      "title": "AI Project: Technology Innovation",
      "short_description": "AI-assisted business opportunity...",
      "full_description": "Comprehensive operational blueprint...",
      "funding_goal": "5000000",
      "minimum_investment": "1000",
      "target_roi": "15",
      "industry_id": 3,
      "industry_name": "Technology",
      "country": "United States",
      "location": "",
      "funding_stage": "Seed",
      "timeline_months": 36,
      "current_status": "Ready for investment pipeline",
      "next_milestones": "Q1: Prototype & MVP\nQ2: Pilot Customers\nQ3: Scale Operations",
      "use_of_funds": "40% R&D, 30% Sales & Marketing, 20% Ops, 10% Reserve",
      "skin_in_the_game": "250000",
      "minimum_contribution": "1000",
      "expected_roi": "15",
      "potential_monthly_revenue": "45000",
      "hold_period_months": 36,
      "timeline_to_operations_months": 1,
      "team_members_text": "Alex Vance (CEO), Maria Santos (CTO), David Chen (CFO)",
      "confidentiality_agreement_text": "Standard NDA required for detailed cap table and audit documents."
    }
  }
}
```

---

### ③ Get Conversation History (for resume/reload)

```
GET /api/v1/ai/projects/conversations/{conversation_id}/
Authorization: Bearer <token>
```

**Response** `200`:
```json
{
  "status": "success",
  "data": {
    "conversation_id": "conv_abc123",
    "step": "description",
    "step_index": 2,
    "total_steps": 4,
    "step_title": "Project Concept",
    "messages": [
      { "id": "msg_001", "role": "assistant", "content": "Hi, I'm Damini...", "timestamp": "...", "suggestions": [...] },
      { "id": "msg_002", "role": "user", "content": "Technology", "timestamp": "...", "suggestions": null },
      { "id": "msg_003", "role": "assistant", "content": "Great! You chose...", "timestamp": "...", "suggestions": [...] }
    ],
    "extracted_data": { "industry": "Technology" },
    "draft": null
  }
}
```

---

### ④ Reset/Delete Conversation

```
DELETE /api/v1/ai/projects/conversations/{conversation_id}/
Authorization: Bearer <token>
```

**Response**: `204 No Content`

My frontend calls this when user taps the reset button in the chat header.

---

## ⚠️ Critical: Draft Field Names

When user taps "Apply Blueprint", I take the `draft` object and pre-fill my project creation form. That form submits to the existing `POST /api/v1/projects/sponsor/` endpoint.

**The draft fields must map to these form field names** (what my `CreateProjectRequestModel.toFormData()` sends):

| Draft Key (from AI response) | Form Field (existing API) | Type Notes |
|---|---|---|
| `title` | `title` | String |
| `short_description` | `short_description` | String |
| `full_description` | `business_description` | ⚠️ Different key name! |
| `funding_goal` | `funding_goal` | Numeric string, no `$` or commas |
| `minimum_investment` | `minimum_investment` | Numeric string |
| `target_roi` | `target_roi` | Numeric string (percentage) |
| `industry_id` | `industry` | **Integer ID** (from `/api/v1/profiles/industries/`) |
| `industry_name` | — | Display only, I need this for UI |
| `country` | `country` | String |
| `location` | `location` | String |
| `funding_stage` | `funding_stage` | String: "Seed", "Series A", etc. |
| `timeline_months` | `timeline_months` | Integer |
| `current_status` | `current_status` | String |
| `next_milestones` | `next_milestones` | String (can be multiline) |
| `use_of_funds` | `use_of_funds` | String |
| `skin_in_the_game` | `skin_in_the_game` | Numeric string |
| `potential_monthly_revenue` | `potential_monthly_revenue` | Numeric string |
| `hold_period_months` | `hold_period_months` | Integer |
| `timeline_to_operations_months` | `timeline_to_operations_months` | Integer |
| `team_members_text` | `team_members_text` | String |
| `confidentiality_agreement_text` | `confidentiality_agreement_text` | String |

> **Important**: I need `industry_id` as integer AND `industry_name` as string. My form sends the integer ID to the create project API, but I display the name in the UI. Currently your industries endpoint is `GET /api/v1/profiles/industries/`.

---

## Step Flow (State Machine)

The conversation goes through these steps in order:

```
industry → description → funding_goal → done
```

| Step | What AI Asks | What User Provides | What You Extract |
|------|-------------|-------------------|-----------------|
| `industry` | "What industry is your project in?" | Industry name or tap chip | `industry` string + resolve to `industry_id` |
| `description` | "Describe your business idea" | Free text | `description` string |
| `funding_goal` | "What's your funding goal?" | Amount (e.g. "$5,000,000") | `funding_goal` numeric string (strip `$` and commas) |
| `done` | "Here's your blueprint!" | — | Generate full draft object |

**If user input is unclear/invalid**: Stay on same step, ask for clarification. Don't advance.

**Suggestions**: Can be dynamic based on context. For industry step, ideally pull from your industries DB. For other steps, AI can generate contextual suggestions.

---

## Error Responses I Handle

I need consistent error shapes:

**422 — Validation Error**:
```json
{
  "status": "error",
  "message": "Validation failed.",
  "errors": {
    "content": ["Message content is required"]
  }
}
```

**404 — Conversation Not Found / Expired**:
```json
{
  "status": "error",
  "message": "Conversation not found or expired."
}
```
→ I'll auto-restart the conversation.

**503 — AI Service Down**:
```json
{
  "status": "error",
  "message": "AI service temporarily unavailable.",
  "retry_after": 30
}
```
→ I'll show a snackbar and disable input for `retry_after` seconds.

**429 — Rate Limited**:
```json
{
  "status": "error",
  "message": "Too many requests.",
  "retry_after": 10
}
```

---

## Edge Cases to Handle

| Scenario | Expected Behavior |
|----------|------------------|
| User sends empty message | Return 422, don't process |
| User sends message after `done` step | Return same draft, don't regenerate |
| User resets mid-conversation | DELETE endpoint clears everything |
| Conversation idle > 24h | Expire it, return 404 on next request |
| User has multiple conversations | Support it or limit to 1 active? (your call, let me know) |
| AI takes too long (>30s) | Timeout, return 503 |
| User provides funding goal as "$5M" | AI should parse to "5000000" |
| User skips a step or answers out of order | AI should guide back to current step |

---

## What I Already Have Working (No Changes Needed)

- ✅ Project form submission: `POST /api/v1/projects/sponsor/` — works fine
- ✅ Industries list: `GET /api/v1/profiles/industries/` — already fetching this
- ✅ Chat UI with messages, typing indicator, suggestion chips
- ✅ Blueprint card rendering
- ✅ Draft → form pre-fill navigation
- ✅ Auth token handling via Dio interceptor

---

## Questions for You

1. **Which AI/LLM** are you planning to use? (OpenAI, Gemini, self-hosted?) — affects how long I should set my loading timeout.

2. **Streaming or REST?** — I currently show a typing indicator while waiting. Regular REST is fine for me, but if you want streaming (SSE), let me know and I'll add support.

3. **Should suggestions come from the industries DB?** — Right now I hardcode 5 industries as chips. If you return them dynamically from DB, I'll just use whatever you send in `suggestions[]`.

4. **Max conversations per user?** — Can a sponsor have multiple AI draft conversations going? Or one at a time?

5. **Should I send `category_ids` in the draft?** — My create project form supports `category_ids[]`. Should AI suggest categories too? If yes, I'll need a categories endpoint.

6. **Cover image** — should AI generate one or leave null for user to upload?

---

## Summary: What I Need to Start Integration

Once you give me these, I can wire everything up on my side:

1. ✅ **Endpoint URLs** confirmed (or adjusted)
2. ✅ **Response shapes** matching what I showed above
3. ✅ `draft` object with all fields from the mapping table
4. ✅ `industry_id` (integer) + `industry_name` (string) in draft
5. ✅ Numeric fields as clean numbers (no `$`, no commas)
6. ✅ Consistent error shapes (`status` + `message` + optional `errors`)

Let me know if you need anything else from my side.
