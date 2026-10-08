# App Missing Endpoints Specification

This document details the exact payloads and responses for the API endpoints listed in Section 1.2 of the Production Readiness Audit. **These endpoints are already implemented and live on the backend.**

---

## 1. Password Reset & Recovery

### 1.1 Request Password Reset OTP
Sends an OTP to the user's email address to initiate a password reset process.
- **Method:** `POST`
- **Endpoint:** `/api/v1/auth/forgot-password/`
- **Auth:** Public

#### Request Body
```json
{
  "email": "user@example.com"
}
```

#### Response `200 OK`
```json
{
  "status": "success",
  "message": "If an account with that email exists, a reset code has been sent."
}
```

---

### 1.2 Reset Password
Verifies the password-reset OTP and sets the new password.
- **Method:** `POST`
- **Endpoint:** `/api/v1/auth/reset-password/`
- **Auth:** Public

#### Request Body
*Note: The backend expects `code` instead of `otp` as requested in the audit report.*
```json
{
  "email": "user@example.com",
  "code": "123456",
  "new_password": "NewSecurePassword123!",
  "confirm_password": "NewSecurePassword123!"
}
```

#### Response `200 OK`
```json
{
  "status": "success",
  "message": "Password reset successfully."
}
```

---

## 2. Change Password (Authenticated)

Changes the authenticated user's password. Requires the old password and a new password.
- **Method:** `POST`
- **Endpoint:** `/api/v1/users/change-password/`
- **Auth:** Bearer Token required

#### Request Body
```json
{
  "current_password": "OldPassword123!",
  "new_password": "NewSecurePassword123!"
}
```

#### Response `200 OK`
```json
{
  "status": "success",
  "message": "Password changed successfully."
}
```

---

## 3. Account Deletion

Permanently deletes the authenticated user's account and all associated data.
*Note: The audit report specified `POST` with `password` and `reason`, but the backend uses a simpler RESTful `DELETE` request with no body required.*

- **Method:** `DELETE`
- **Endpoint:** `/api/v1/users/delete-account/`
- **Auth:** Bearer Token required

#### Request Body
*(None required)*

#### Response `200 OK`
```json
{
  "status": "success",
  "message": "Account deleted successfully."
}
```

---

## 4. Sponsor NDA & Pitch Deck Management

### 4.1 Fetch Sponsor NDA Terms
Retrieves the authenticated sponsor's active NDA configuration and confidential attachments.
- **Method:** `GET`
- **Endpoint:** `/api/v1/profiles/sponsor/nda/`
- **Auth:** Bearer Token (Sponsor) required

#### Response `200 OK`
```json
{
  "status": "success",
  "data": {
    "title": "Non-Disclosure Agreement",
    "disclosing_party": "Acme Capital",
    "effective_date": "2026-08-15",
    "confidentiality_terms": "These are the standard confidentiality terms...",
    "pitch_deck_file": {
      "file_name": "pitch_deck_v2.pdf",
      "file_url": "https://example.com/media/nda/pitch_deck_v2.pdf",
      "file_size": "12.4 MB"
    },
    "custom_clauses": [
      "Clause 1: Non-compete...",
      "Clause 2: Jurisdiction..."
    ]
  }
}
```

### 4.2 Update Terms & Upload Pitch Deck
Updates the sponsor's active NDA configuration. Accepts multipart/form-data for file uploads.
- **Method:** `POST`
- **Endpoint:** `/api/v1/profiles/sponsor/nda/`
- **Auth:** Bearer Token (Sponsor) required
- **Content-Type:** `multipart/form-data`

#### Request Payload
- `confidentiality_terms` (text, optional)
- `pitch_deck` (file upload - PDF only, max 25MB, optional)
- `custom_clauses` (JSON array string, optional)

#### Response `200 OK`
```json
{
  "status": "success",
  "message": "NDA details and confidential attachments updated successfully.",
  "data": {
    "disclosing_party": "Acme Capital",
    "confidentiality_terms": "Updated terms...",
    "pitch_deck_file": {
      "file_name": "new_pitch_deck.pdf",
      "file_url": "https://example.com/media/nda/new_pitch_deck.pdf",
      "file_size": "4.2 MB"
    },
    "custom_clauses": ["Updated clause"]
  }
}
```
