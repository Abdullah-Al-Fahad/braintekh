# Investor Role — Complete Backend API Specification & Gap Analysis

Comprehensive API contract and static data audit for the **Investor** module (`lib/views/investor/`).

---

## 1. Executive Summary & Audit of Investor Module

| Feature / Screen | File Location | Current State in Flutter | Remaining Backend API Needed |
|---|---|---|---|
| **Investor Dashboard** | `lib/views/investor/dashboard/` | ⚠️ Partially Connected (`/users/me/`, `/profiles/industries/`, `/projects/`). Banners & featured filters hardcoded. | `GET /api/v1/banners/`<br>`GET /api/v1/investor/dashboard/` |
| **Discover Deals & Filters** | `lib/views/investor/discover/` | ❌ **100% Mock Static Data** (`DiscoverRepositoryImpl`) | `GET /api/v1/projects/discover/` (with filters & sorting) |
| **Investment History & Portfolio** | `lib/views/investor/investment_history/` | ❌ **100% Mock Static Data** (`InvestmentHistoryRepositoryImpl`) | `GET /api/v1/investor/investments/`<br>`GET /api/v1/investor/portfolio-summary/` |
| **Saved Projects & Bookmarks** | `lib/views/investor/saved/` | ❌ **100% Mock Static Data** (`InvestorSavedRepositoryImpl`) | `GET /api/v1/projects/saved/`<br>`POST /api/v1/projects/{id}/save/` |
| **Collaboration Request** | `lib/views/investor/request_collaboration/` | ⚠️ Endpoint defined (`POST /api/v1/projects/{id}/requests/`) | Needs full backend handling & status tracking |
| **Investor Chat & Conversations** | `lib/views/investor/chat/` | ❌ **100% Mock Static Data** (`InvestorChatRepositoryImpl`) | `GET /api/v1/notifications/chat/conversations/`<br>WebSocket real-time chat |
| **Project Details (Investor View)** | `lib/views/sponsor/public_view/` | ⚠️ Partially connected (`GET /api/v1/projects/{id}/`) | Rich metrics, documents, sponsor NDA status |
| **NDA Signing** | `lib/views/sponsor/nda/` | ⚠️ Endpoint defined (`POST /api/v1/projects/{id}/sign-nda/`) | Backend PDF generation / signature verification |

---

## 2. Detailed API Specifications

### 2.1. Promotional Banners API

Replaces static banner list in `InvestorDashboardRepositoryImpl.getBanners()`.

- **Method:** `GET`
- **Endpoint:** `/api/v1/banners/`
- **Query Params:** `role=investor` (optional)
- **Auth:** Optional / Bearer Token

#### Response `200 OK`
```json
{
  "success": true,
  "data": [
    {
      "id": "banner_1",
      "title": "Exclusive Tech Seed Rounds",
      "subtitle": "Direct co-investment opportunities with verified lead syndicates.",
      "tag": "High Yield",
      "bg_gradient": ["#0F1E2E", "#162A3D"],
      "image_url": "https://example.com/banners/tech_seed.png",
      "action_text": "Explore Rounds",
      "action_url": "/discover?category=Tech",
      "target_project_id": null
    },
    {
      "id": "banner_2",
      "title": "Prime Commercial Real Estate",
      "subtitle": "Institutional grade assets structured for steady dividend yields.",
      "tag": "Featured",
      "bg_gradient": ["#1E162D", "#2A1C3D"],
      "image_url": "https://example.com/banners/real_estate.png",
      "action_text": "View Assets",
      "action_url": "/discover?category=Real+Estate",
      "target_project_id": "proj_downtown_tech"
    }
  ]
}
```

---

### 2.2. Discover Deals & Feed API (Search, Category, Filter, Sort)

Replaces mock list in `DiscoverRepositoryImpl.getDiscoverDeals()`.

- **Method:** `GET`
- **Endpoint:** `/api/v1/projects/discover/` (or `/api/v1/projects/`)
- **Auth:** Bearer Token required
- **Query Parameters:**
  - `category` (string, e.g. `Tech`, `Real Estate`, `Health`, `Energy`, `All`)
  - `search` (string query)
  - `min_roi` (number, e.g. `15.0`)
  - `max_roi` (number)
  - `min_raise` (number, e.g. `100000`)
  - `max_raise` (number)
  - `sort_by` (`highest_roi` | `lowest_roi` | `newest` | `highest_raise` | `lowest_raise` | `closing_soon`)
  - `page` (int, default `1`)
  - `page_size` (int, default `20`)

#### Response `200 OK`
```json
{
  "success": true,
  "data": {
    "count": 42,
    "next": "/api/v1/projects/discover/?page=2",
    "previous": null,
    "results": [
      {
        "id": "proj_9876",
        "title": "Downtown Tech Hub",
        "location": "United States",
        "category": "Real Estate",
        "image_url": "https://images.unsplash.com/photo-1497366216548-37526070297c?q=80&w=600&auto=format&fit=crop",
        "target_raise": "$5,000,000",
        "raise_value": 5000000,
        "min_investment": "$1,000",
        "min_investment_value": 1000,
        "target_roi": "~ 18%",
        "roi_value": 18.0,
        "funded_percent": 0.75,
        "days_left": 14,
        "is_saved": false,
        "sponsor": {
          "id": "usr_sponsor_1",
          "name": "Acme Capital",
          "is_verified": true
        },
        "created_at": "2026-10-01T12:00:00.000Z"
      }
    ]
  }
}
```

---

### 2.3. Investor Investment History & Portfolio

Replaces mock list in `InvestmentHistoryRepositoryImpl.getInvestmentRecords()`.

#### A. List Investor's Investments
- **Method:** `GET`
- **Endpoint:** `/api/v1/investor/investments/`
- **Auth:** Bearer Token required
- **Query Params:**
  - `status` (`all` | `active` | `completed` | `pending` | `cancelled`)
  - `page` (int, default `1`)
  - `page_size` (int, default `20`)

#### Response `200 OK`
```json
{
  "success": true,
  "data": {
    "summary": {
      "total_invested": "$560,000",
      "total_current_value": "$644,200",
      "overall_roi": "+15.03%",
      "active_investments_count": 3
    },
    "count": 4,
    "next": null,
    "previous": null,
    "results": [
      {
        "id": "inv_rec_101",
        "project_id": "proj_9876",
        "title": "Downtown Tech Hub",
        "category": "Real Estate",
        "sponsor_name": "Acme Corp",
        "sponsor_id": "usr_sponsor_1",
        "investment_date": "2026-03-14T00:00:00.000Z",
        "formatted_date": "Mar 14, 2026",
        "status": "Active",
        "invested_amount": 250000.00,
        "formatted_invested": "$250,000",
        "current_value": 288000.00,
        "formatted_current_value": "$288,000",
        "roi": "+15.2%",
        "image_url": "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?q=80&w=300&auto=format&fit=crop"
      },
      {
        "id": "inv_rec_102",
        "project_id": "proj_5544",
        "title": "AI Logistics Platform",
        "category": "Tech",
        "sponsor_name": "Nexus AI",
        "sponsor_id": "usr_sponsor_2",
        "investment_date": "2026-02-22T00:00:00.000Z",
        "formatted_date": "Feb 22, 2026",
        "status": "Active",
        "invested_amount": 150000.00,
        "formatted_invested": "$150,000",
        "current_value": 173000.00,
        "formatted_current_value": "$173,000",
        "roi": "+15.3%",
        "image_url": "https://images.unsplash.com/photo-1518770660439-4636190af475?q=80&w=300&auto=format&fit=crop"
      }
    ]
  }
}
```

---

### 2.4. Investor Saved / Bookmarked Projects

Replaces mock list in `InvestorSavedRepositoryImpl.getSavedItems()`.

#### A. Fetch Saved Projects List
- **Method:** `GET`
- **Endpoint:** `/api/v1/projects/saved/`
- **Auth:** Bearer Token required
- **Query Params:**
  - `status` (optional filter: `all` | `active` | `pending`)
  - `page` & `page_size`

#### Response `200 OK`
```json
{
  "success": true,
  "data": {
    "count": 4,
    "results": [
      {
        "id": "proj_9876",
        "saved_item_id": "save_rec_01",
        "title": "Downtown Tech Hub",
        "category": "Real Estate",
        "saved_date": "2026-02-22T10:00:00.000Z",
        "formatted_date": "Feb 22, 2026",
        "status": "Active",
        "invested": "$250k",
        "value": "$288k",
        "target_roi": "+15.0%",
        "funding_progress": 0.24,
        "image_url": "https://images.unsplash.com/photo-1486406146926-c627a92ad1ab?q=80&w=300&auto=format&fit=crop"
      }
    ]
  }
}
```

#### B. Toggle Save / Bookmark Project
- **Method:** `POST`
- **Endpoint:** `/api/v1/projects/{project_id}/save/`
- **Auth:** Bearer Token required

#### Response `200 OK`
```json
{
  "success": true,
  "is_saved": true,
  "message": "Project saved successfully."
}
```

---

### 2.5. Submit Collaboration Request (Express Interest / Deal Flow)

Connects `RequestCollaborationRepositoryImpl.submitCollaborationRequest()`.

- **Method:** `POST`
- **Endpoint:** `/api/v1/projects/{project_id}/requests/`
- **Auth:** Bearer Token required

#### Request Body
```json
{
  "proposed_budget": 50000,
  "message": "We would like to participate in this seed round as a strategic investor."
}
```

#### Response `201 Created`
```json
{
  "success": true,
  "message": "Collaboration request submitted successfully to project sponsor.",
  "data": {
    "request_id": "collab_req_8765",
    "project_id": "proj_9876",
    "status": "PENDING",
    "proposed_budget": 50000,
    "created_at": "2026-10-08T10:15:00.000Z"
  }
}
```

---

### 2.6. Investor Chat / Sponsor Direct Messages

Replaces mock list in `InvestorChatRepositoryImpl.getChats()`.

#### A. List Active Investor Chat Threads
- **Method:** `GET`
- **Endpoint:** `/api/v1/notifications/chat/conversations/`
- **Auth:** Bearer Token required

#### Response `200 OK`
```json
{
  "success": true,
  "data": {
    "count": 3,
    "results": [
      {
        "id": "conv_123",
        "name": "Acme Investments (Lead Sponsor)",
        "project_id": "proj_9876",
        "last_message": "The term sheet has been uploaded to the deal room.",
        "time": "10:42 AM",
        "last_message_time": "2026-10-08T10:42:00.000Z",
        "unread_count": 2,
        "avatar_url": "https://images.unsplash.com/photo-1534528741775-53994a69daeb?q=80&w=150&auto=format&fit=crop",
        "is_group_chat": false
      },
      {
        "id": "conv_124",
        "name": "Downtown Tech Hub Syndicate",
        "project_id": "proj_9876",
        "last_message": "Q1 investor call scheduled for this Thursday.",
        "time": "Yesterday",
        "last_message_time": "2026-10-07T16:00:00.000Z",
        "unread_count": 0,
        "avatar_url": "https://images.unsplash.com/photo-1497366216548-37526070297c?q=80&w=150&auto=format&fit=crop",
        "is_group_chat": true
      }
    ]
  }
}
```

#### B. Start / Open Chat With Project Sponsor
- **Method:** `POST`
- **Endpoint:** `/api/v1/notifications/chat/conversations/start/`
- **Auth:** Bearer Token required

#### Request Body
```json
{
  "sponsor_id": "usr_sponsor_1",
  "project_id": "proj_9876"
}
```

#### Response `200 OK`
```json
{
  "success": true,
  "data": {
    "conversation_id": "conv_123",
    "is_new": false
  }
}
```

---

### 2.7. Sign Project NDA (Non-Disclosure Agreement)

Connects `POST /api/v1/projects/{project_id}/sign-nda/`.

- **Method:** `POST`
- **Endpoint:** `/api/v1/projects/{project_id}/sign-nda/`
- **Auth:** Bearer Token required

#### Request Body
```json
{
  "full_name": "John Doe",
  "signature_date": "2026-10-08",
  "accepted_terms": true
}
```

#### Response `200 OK`
```json
{
  "success": true,
  "message": "NDA signed successfully. Full project documents unlocked.",
  "data": {
    "nda_id": "nda_sig_54321",
    "signed_at": "2026-10-08T10:20:00.000Z",
    "pdf_url": "https://storage.googleapis.com/damini-ai/nda/signed_nda_54321.pdf"
  }
}
```

---

## 3. Dart Model ↔ Backend JSON Key Reference

| Feature | Model Class | Backend JSON Key | Dart Property | Data Type |
|---|---|---|---|---|
| **Dashboard** | `InvestorBannerModel` | `title` | `title` | `String` |
| | | `subtitle` | `subtitle` | `String` |
| | | `tag` | `tag` | `String` |
| | | `action_text` | `actionText` | `String` |
| | `TrendingProjectModel` | `title` | `title` | `String` |
| | | `funded_percent` | `fundedPercent` | `double` (0.0 - 1.0) |
| | | `min_investment` | `minInvestment` | `String` |
| | | `days_left` | `daysLeft` | `int` |
| **Discover** | `DiscoverDealItem` | `id` | `id` | `String` |
| | | `category` | `category` | `String` |
| | | `target_raise` | `targetRaise` | `String` |
| | | `raise_value` | `raiseValue` | `double` / `int` |
| | | `target_roi` | `targetRoi` | `String` |
| | | `roi_value` | `roiValue` | `double` |
| **History** | `InvestmentRecordModel` | `id` | `id` | `String` |
| | | `sponsor_name` | `sponsor` | `String` |
| | | `formatted_date` | `date` | `String` |
| | | `status` | `status` | `String` (`Active`, `Completed`, `Pending`) |
| | | `formatted_invested` | `invested` | `String` |
| | | `formatted_current_value` | `currentValue` | `String` |
| | | `roi` | `roi` | `String` |
| **Saved** | `InvestorSavedItemModel` | `id` | `id` | `String` |
| | | `funding_progress` | `fundingProgress` | `double` (0.0 - 1.0) |
| | | `status` | `status` | `String` |
| **Chat** | `InvestorChatItemModel` | `id` | `id` | `String` |
| | | `name` | `name` | `String` |
| | | `last_message` | `lastMessage` | `String` |
| | | `time` | `time` | `String` |
| | | `unread_count` | `unreadCount` | `int` |
| | | `is_group_chat` | `isGroupChat` | `bool` |
