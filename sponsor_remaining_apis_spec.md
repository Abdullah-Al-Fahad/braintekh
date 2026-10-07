![alt text](https://example.com)# Sponsor Role — Remaining Backend APIs Specification

This document details the backend endpoints and requirements identified during the Sponsor Role audit for **DiasporaVest / Braintech**.

---

## 1. Executive Summary & Gaps Addressed

The audit of the Sponsor role identified **3 missing API flows** and **1 endpoint enhancement** required for complete end-to-end integration:

| Priority | Module | Proposed Endpoint | Purpose |
| :--- | :--- | :--- | :--- |
| **High** | **Sponsor NDA Management** | `GET /api/v1/profiles/sponsor/nda/`<br>`POST /api/v1/profiles/sponsor/nda/` | Allows sponsors to view, customize NDA terms, and upload their Pitch Deck & Financials. |
| **High** | **Account Deletion** | `POST /api/v1/users/delete-account/`<br>or `DELETE /api/v1/users/me/` | Securely verifies password, cleans up sessions, and soft-deletes the sponsor account. |
| **Medium** | **Company Verification** | `POST /api/v1/profiles/verification-documents/`<br>`GET /api/v1/profiles/verification-status/` | Unifying profile-level verification document uploads with onboarding models. |
| **Medium** | **Project Details Context** | `GET /api/v1/projects/<id>/` | Returning `is_saved`, `nda_status`, and sponsor details in the public/detail payload. |

---

## 2. Sponsor NDA & Pitch Deck Management

### Context
Sponsors access the NDA flow from **Profile Menu** -> **Non-Disclosure Agreement** (`/nda`), with an **Edit** action (`/edit-nda`) to configure their confidentiality terms and upload confidential investor documents (Pitch Deck & Financials).

Currently, the mobile client falls back to static mock text and a dummy sample PDF.

---

### 2.1 Get Sponsor NDA Template & Documents
#### `GET /api/v1/profiles/sponsor/nda/`
Retrieves the authenticated sponsor's active NDA configuration and confidential attachments.

#### Headers
| Header | Value | Description |
| :--- | :--- | :--- |
| `Authorization` | `Bearer <access_token>` | Sponsor's JWT token |

#### Response (`200 OK`)
```json
{
  "status": "success",
  "data": {
    "title": "Non-Disclosure Agreement",
    "disclosing_party": "Acme Holdings LLC",
    "effective_date": "2026-10-06",
    "confidentiality_terms": "This Non-Disclosure Agreement governs the disclosure of confidential and proprietary information between the parties. By signing below, you agree to keep all disclosed materials strictly confidential and use them solely for evaluation purposes.",
    "pitch_deck_file": {
      "file_name": "Acme_Pitch_Deck_Financials_v2.pdf",
      "file_url": "https://clubby-andy-irksomely.ngrok-free.dev/media/sponsor_ndas/Acme_Pitch_Deck_Financials_v2.pdf",
      "file_size": "3.4 MB",
      "uploaded_at": "2026-10-01T14:22:10Z"
    },
    "custom_clauses": [
      "Recipient agrees not to disclose trade secrets or proprietary algorithms.",
      "Non-solicitation of key executive and technical staff for a period of 24 months."
    ]
  }
}
```

---

### 2.2 Update Sponsor NDA & Upload Pitch Deck
#### `POST /api/v1/profiles/sponsor/nda/` (or `PUT /api/v1/profiles/sponsor/nda/`)
Updates confidentiality explanation terms and uploads a new Pitch Deck & Financials document.

#### Content-Type
`multipart/form-data`

#### Request Parameters
| Field | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `confidentiality_terms` | `string` | Optional | Updated explanation of the confidentiality agreement. |
| `pitch_deck` | `file` (PDF) | Optional | The PDF document of Pitch Deck & Financials (Max 25 MB). |
| `custom_clauses` | `string` (JSON array) | Optional | Optional custom clauses list (e.g. `["Clause 1", "Clause 2"]`). |

#### Response (`200 OK` or `201 Created`)
```json
{
  "status": "success",
  "message": "NDA details and confidential attachments updated successfully.",
  "data": {
    "disclosing_party": "Acme Holdings LLC",
    "confidentiality_terms": "Updated explanation....",
    "pitch_deck_file": {
      "file_name": "Pitch_Deck_Financials_v3.pdf",
      "file_url": "https://clubby-andy-irksomely.ngrok-free.dev/media/sponsor_ndas/Pitch_Deck_Financials_v3.pdf",
      "file_size": "4.1 MB",
      "uploaded_at": "2026-10-06T15:30:00Z"
    }
  }
}
```

#### Error Handling
* `400 Bad Request`: File is not a valid PDF or exceeds 25 MB limit.
* `401 Unauthorized`: Missing or expired JWT token.
* `403 Forbidden`: Authenticated user is not in the `SPONSOR` role.

---

## 3. Account Deletion Flow

### Context
In **Settings** (`/settings`), users have a **Delete Account** button. The mobile client presents a dialog requiring:
1. Re-entering their account password.
2. A mandatory 5-second countdown timer.

Currently, the app performs only a local `logout()`. We need a secure backend endpoint to process account termination.

---

### 3.1 Endpoint
#### `POST /api/v1/users/delete-account/` (or `DELETE /api/v1/users/me/`)

#### Headers
| Header | Value | Description |
| :--- | :--- | :--- |
| `Authorization` | `Bearer <access_token>` | User's JWT token |
| `Content-Type` | `application/json` | |

#### Request Body
```json
{
  "password": "UserCurrentPassword123!",
  "confirmation": "DELETE"
}
```

| Field | Type | Required | Description |
| :--- | :--- | :---: | :--- |
| `password` | `string` | ✅ Yes | The user's current account password for authorization. |
| `confirmation` | `string` | Optional | Explicit string `"DELETE"` as a safeguard. |

#### Backend Processing Requirements
1. **Password Verification:** Validate `password` against the user's hashed password (`check_password()`). Return `400 Bad Request` if incorrect.
2. **Soft Deletion / Anonymization:**
   - Set `user.is_active = False`.
   - Set `user.deleted_at = timezone.now()`.
   - Clear/anonymize sensitive personal data (e.g. email prefixed with `deleted_<uuid>_`, clear device push tokens).
3. **Project Handling (For Sponsors):**
   - Automatically change any `ACTIVE` projects owned by this sponsor to `TERMINATED` with reason `"Account deleted by sponsor"`.
4. **Token Blacklist:** Invalidate all active refresh tokens and blacklist current JWT tokens.

#### Success Response (`200 OK`)
```json
{
  "status": "success",
  "message": "Account has been deleted successfully. You have been logged out."
}
```

#### Error Responses
| Status | Scenario | Response Body |
| :--- | :--- | :--- |
| `400 Bad Request` | Incorrect password | `{"error": "Incorrect password. Please verify and try again."}` |
| `401 Unauthorized` | Invalid/expired token | `{"detail": "Authentication credentials were not provided."}` |

---

## 4. Company Verification in Sponsor Profile

### Context
When a sponsor registers as a Company or updates their business status, they access **Profile** -> **Company Verification** (`/company-verification`).

During onboarding, `OnboardingRepository` uses:
* `POST /api/v1/profiles/verification-documents/`
* `GET /api/v1/profiles/verification-status/`

However, inside the active app profile, `CompanyVerificationRepository` had mock delays and hardcoded company details. We are hooking it up to the existing backend endpoints.

### Expected Payload for `POST /api/v1/profiles/verification-documents/`
`multipart/form-data`
```
document_type: "BUSINESS_REGISTRATION" | "TAX_DOCUMENT" | "PROOF_OF_ADDRESS"
file: <binary_file> (PDF / JPG / PNG)
```

### Expected Response for `GET /api/v1/profiles/verification-status/`
```json
{
  "status": "PENDING",
  "company_name": "Apex Ventures Ltd.",
  "registration_number": "REG-88921-X",
  "address": "100 Montgomery St, Suite 400, San Francisco, CA",
  "website": "https://apexventures.com",
  "documents": [
    {
      "id": 12,
      "document_type": "BUSINESS_REGISTRATION",
      "file_url": "https://clubby-andy-irksomely.ngrok-free.dev/media/verifications/license.pdf",
      "uploaded_at": "2026-10-05T09:15:00Z"
    }
  ],
  "rejection_reason": null
}
```

---

## 5. Single Project Details Response Enhancement

### Endpoint: `GET /api/v1/projects/<id>/`
To prevent client-side mock fallbacks when viewing project details or public view, ensure the payload returns these additional context flags:

```json
{
  "id": 3,
  "title": "Downtown Tech Hub",
  "status": "ACTIVE",
  "is_saved": false,
  "sponsor": {
    "id": 14,
    "name": "Acme Holdings LLC",
    "avatar": "https://.../sponsor.jpg",
    "verification_status": "APPROVED"
  },
  "nda_requirement": {
    "is_required": true,
    "user_has_signed": false,
    "signed_at": null
  },
  "collaboration_request": {
    "has_requested": false,
    "status": null
  },
  "confidential_documents": [
    {
      "id": 1,
      "title": "Confidential Cap Table & Financials",
      "file_size": "2.4 MB",
      "is_locked": true
    }
  ]
}
```

* `is_saved`: Whether the currently authenticated user bookmarked this project.
* `nda_requirement.user_has_signed`: `true` if this user already signed the NDA for this project, allowing the client to unlock confidential document downloads.
* `collaboration_request`: Current status of the user's collaboration request (`PENDING`, `APPROVED`, `REJECTED`, or `null`).

---

## 6. Checklist for Backend Developer

- [ ] **Sponsor NDA Endpoints**:
  - [ ] Implement `GET /api/v1/profiles/sponsor/nda/`.
  - [ ] Implement `POST /api/v1/profiles/sponsor/nda/` with multipart file upload support.
- [ ] **Account Deletion Endpoint**:
  - [ ] Implement `POST /api/v1/users/delete-account/` with password verification and soft-deletion.
  - [ ] Cascade auto-termination of the sponsor's active projects.
- [ ] **Company Verification**:
  - [ ] Ensure `verification-status` returns existing company metadata and document list for profile viewing.
- [ ] **Project Context Flags**:
  - [ ] Confirm `is_saved` and `user_has_signed` flags are included in `GET /api/v1/projects/<id>/`.
