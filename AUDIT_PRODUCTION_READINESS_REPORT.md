# Braintech Application — Comprehensive Production Readiness & End-to-End Audit Report

**Date:** 2026-10-08  
**Audit Scope:** Full Application Audit (R1: Static/Mock Data, R2: Navigation & User Flows, R3: Backend & API Robustness, R4: UX/UI & Consistency, R5: Production Readiness & QA)  
**Target Codebase:** `d:\Ismail_flutter\julkar_vai`

---

## Executive Summary & Readiness Scorecard

| Area | Status | Score | Key Findings |
| :--- | :---: | :---: | :--- |
| **R1: Data & API Integration** | ⚠️ Attention Needed | **78%** | 3 auth stubs (`Future.delayed`), orphaned `lib/data/`, pure mock Subscription module, 4 fallback mocks. |
| **R2: User Flows & Navigation** | ⚠️ Attention Needed | **72%** | Parameter mismatches on Banner & Deal details, investor group chat uninitialized, missing PopScopes on wizards. |
| **R3: Backend & API Robustness** | ⚠️ Attention Needed | **80%** | SSL badCertificateCallback enabled unconditionally, .env in assets, silent error catching in repositories. |
| **R4: UX / UI Consistency** | ⚠️ Minor Issues | **85%** | Keyboard overflow risk with `Spacer()` on auth screens, hardcoded `Colors.white` in onboarding, missing shimmers in Investor tabs. |
| **R5: Code Health & QA** | ✅ Ready | **92%** | `dart analyze` passes with **0 issues**, 13/14 test suites passing (97+ tests green). |

---

## 1. R1: Static & Mock Data Remnants & Missing API Catalog

### 1.1 Hardcoded Mocks & Stubs Catalog

| Component / File Path | Type | Details / Root Cause | Remediation Action |
| :--- | :---: | :--- | :--- |
| [`lib/views/auth/forgot_password/repositories/forgot_password_repository.dart`](file:///d:/Ismail_flutter/julkar_vai/lib/views/auth/forgot_password/repositories/forgot_password_repository.dart#L12) | **Stub** | `sendOtp()` uses `Future.delayed(1s)` returning static success. | Connect to `POST /api/v1/auth/forgot-password/` |
| [`lib/views/auth/reset_password/repositories/reset_password_repository.dart`](file:///d:/Ismail_flutter/julkar_vai/lib/views/auth/reset_password/repositories/reset_password_repository.dart#L12) | **Stub** | `resetPassword()` uses `Future.delayed(1s)` returning static success. | Connect to `POST /api/v1/auth/reset-password/` |
| [`lib/views/auth/change_password/controllers/change_password_provider.dart`](file:///d:/Ismail_flutter/julkar_vai/lib/views/auth/change_password/controllers/change_password_provider.dart#L25) | **Stub** | `changePassword()` uses `Future.delayed(1s)` without repository. | Connect to `POST /api/v1/users/change-password/` |
| [`lib/views/subscription/controllers/subscription_provider.dart`](file:///d:/Ismail_flutter/julkar_vai/lib/views/subscription/controllers/subscription_provider.dart#L10) | **Pure Mock** | Plans hardcoded in memory, no payment gateway or API. | Connect to `GET /api/v1/subscriptions/plans/` & payment checkout |
| [`lib/data/services/opportunity_service.dart`](file:///d:/Ismail_flutter/julkar_vai/lib/data/services/opportunity_service.dart#L8) | **Orphaned Stub** | Unused `OpportunityService` with `Future.delayed(800ms)`. | Safe to delete / deprecate |
| [`lib/views/settings/repositories/settings_repository.dart`](file:///d:/Ismail_flutter/julkar_vai/lib/views/settings/repositories/settings_repository.dart#L10) | **Pure Mock** | Account deletion and toggle preferences not persisted. | Connect to `POST /api/v1/users/delete-account/` |
| [`lib/views/sponsor/nda/screens/nda_view.dart`](file:///d:/Ismail_flutter/julkar_vai/lib/views/sponsor/nda/screens/nda_view.dart#L20) | **Pure Mock** | Sponsor NDA terms and pitch deck upload not wired to API. | Connect to `GET/POST /api/v1/profiles/sponsor/nda/` |

---

### 1.2 Missing Backend Endpoints Specification

#### 1. Password Reset & Recovery
- **Request OTP:** `POST /api/v1/auth/forgot-password/`
  ```json
  { "email": "user@example.com" }
  ```
- **Reset Password:** `POST /api/v1/auth/reset-password/`
  ```json
  {
    "email": "user@example.com",
    "otp": "123456",
    "new_password": "NewSecurePassword123!",
    "confirm_password": "NewSecurePassword123!"
  }
  ```

#### 2. Change Password (Authenticated)
- **Endpoint:** `POST /api/v1/users/change-password/`
  ```json
  {
    "current_password": "OldPassword123!",
    "new_password": "NewSecurePassword123!"
  }
  ```

#### 3. Account Deletion
- **Endpoint:** `POST /api/v1/users/delete-account/`
  ```json
  {
    "password": "UserPassword123!",
    "reason": "No longer need the service"
  }
  ```

#### 4. Sponsor NDA & Pitch Deck Management
- **Fetch Terms:** `GET /api/v1/profiles/sponsor/nda/`
- **Update Terms & Upload Deck:** `POST /api/v1/profiles/sponsor/nda/` (multipart/form-data with `pitch_deck` PDF).

---

## 2. R2: User Flows & Navigation Verification

### 2.1 Critical Navigation Bugs Found & Remediation

1. **Investor Dashboard Banner Parameter Mismatch:**
   - **File:** [`investor_banner_carousel.dart:235`](file:///d:/Ismail_flutter/julkar_vai/lib/views/investor/dashboard/widgets/investor_banner_carousel.dart#L235) vs [`app_router.dart:286`](file:///d:/Ismail_flutter/julkar_vai/lib/core/routing/app_router.dart#L286)
   - **Issue:** Banner passes `extra: {'projectId': item.targetProjectId}`, but router only looks for `extraMap['id']`. `projectId` becomes `null` and `ProjectPublicView` falls back to mock data.
   - **Fix:** In `app_router.dart`, check `extraMap['id'] ?? extraMap['projectId']`.

2. **Investment History Deal Details Missing Argument:**
   - **File:** [`investment_history_screen.dart:477`](file:///d:/Ismail_flutter/julkar_vai/lib/views/investor/investment_history/screens/investment_history_screen.dart#L477)
   - **Issue:** `context.push('/public-view')` is called without `extra: {'id': item.projectId}`.
   - **Fix:** Pass `extra: {'id': item.projectId}`.

3. **Investor Group Chat Argument Mismatch:**
   - **File:** [`investor_chat_view.dart:138`](file:///d:/Ismail_flutter/julkar_vai/lib/views/investor/chat/screens/investor_chat_view.dart#L138) vs [`sponsor_chat_view.dart:93`](file:///d:/Ismail_flutter/julkar_vai/lib/views/sponsor/chat/screens/sponsor_chat_view.dart#L93)
   - **Issue:** Passes raw `chat.name` instead of `Map` containing `conversationId` and `projectId`. WebSocket connection fails and chat opens empty.
   - **Fix:** Pass Map with `title`, `conversationId`, and `projectId`.

4. **Synthetic String Chat IDs:**
   - **File:** [`investor_saved_project_card.dart:152`](file:///d:/Ismail_flutter/julkar_vai/lib/views/investor/saved/widgets/investor_saved_project_card.dart#L152) and [`public_profile_view.dart:255`](file:///d:/Ismail_flutter/julkar_vai/lib/views/profile/public_profile/screens/public_profile_view.dart#L255)
   - **Issue:** Passes `"chat_${item.id}"` which causes `int.tryParse()` to fail in `DirectChatProvider`, triggering permanent mock fallback.
   - **Fix:** Call `startConversation` API to obtain real backend conversation ID before opening direct chat.

5. **`ResetPasswordView` Crash on Back Button:**
   - **File:** [`reset_password_view.dart:78`](file:///d:/Ismail_flutter/julkar_vai/lib/views/auth/reset_password/screens/reset_password_view.dart#L78)
   - **Issue:** `IconButton` calls `context.pop()` after screen was navigated via `context.go('/reset-password')`. This crashes with `GoError: There is nothing to pop`.
   - **Fix:** Check `if (context.canPop()) context.pop(); else context.go('/login');`.

6. **Missing PopScope on Multi-Step Onboarding Wizard:**
   - **File:** [`role_onboarding_view.dart:127`](file:///d:/Ismail_flutter/julkar_vai/lib/views/role_selection/role_onboarding_view.dart#L127)
   - **Issue:** Pressing Android hardware back button immediately exits onboarding instead of decrementing `_pageCtrl.previousPage()`.
   - **Fix:** Wrap with `PopScope(canPop: _currentPage == 0, onPopInvokedWithResult: ...)` to handle internal page back navigation.

---

## 3. R3: Backend Integration & API Robustness

1. **Security — TLS / SSL Certificate Validation:**
   - **File:** [`dio_service.dart:65`](file:///d:/Ismail_flutter/julkar_vai/lib/core/services/dio_service.dart#L65)
   - **Issue:** `badCertificateCallback = (cert, host, port) => true;` allows MITM attacks in production.
   - **Fix:** Gate with `if (kDebugMode) { badCertificateCallback = ... }`.

2. **Security — `.env` Exposure:**
   - **File:** [`pubspec.yaml:69`](file:///d:/Ismail_flutter/julkar_vai/pubspec.yaml#L69)
   - **Recommendation:** Ensure `.env` is omitted from production builds or sensitive backend keys are replaced by build arguments.

3. **Investor Profile Data Fetch:**
   - **File:** [`sponsor_edit_profile_repository.dart:34`](file:///d:/Ismail_flutter/julkar_vai/lib/views/profile/personal_info/repositories/sponsor_edit_profile_repository.dart#L34)
   - **Issue:** Skips fetching full profile when `role == 'investor'`.
   - **Fix:** Use `ApiEndpoints.profileByRole(role)` for both investor and sponsor.

---

## 4. R4: UX / UI Consistency & Edge Cases

1. **Keyboard Overflow Vulnerability:**
   - **Files:** [`forgot_password_view.dart`](file:///d:/Ismail_flutter/julkar_vai/lib/views/auth/forgot_password/screens/forgot_password_view.dart), [`otp_verification_view.dart`](file:///d:/Ismail_flutter/julkar_vai/lib/views/auth/otp/screens/otp_verification_view.dart), [`reset_password_view.dart`](file:///d:/Ismail_flutter/julkar_vai/lib/views/auth/reset_password/screens/reset_password_view.dart), [`choose_type_screen.dart`](file:///d:/Ismail_flutter/julkar_vai/lib/shared/screens/choose_type_screen.dart).
   - **Fix:** Replace `const Spacer()` inside unscrollable `Column` with `SingleChildScrollView` + `LayoutBuilder` + `ConstrainedBox`.

2. **Investor Screens Shimmer & Error Handling:**
   - **Files:** `InvestorDashboard`, `DiscoverScreen`, `InvestorSavedView`, `InvestmentHistoryScreen`.
   - **Fix:** Standardize on `AppShimmer`, `AppErrorView`, and `AppEmptyView` across all investor tabs matching the sponsor module.

3. **Light Mode Theme Contrast:**
   - **Files:** `onboarding_widgets.dart`, `role_selection_view.dart`, `choose_type_screen.dart`.
   - **Fix:** Replace hardcoded `Colors.white` with `AppThemeColors.of(context).textPrimary`.

---

## 5. R5: Code Health & Verification

1. **Static Analysis:**
   - `dart analyze`: **0 errors, 0 warnings, 0 lints**.
2. **Automated Test Suite:**
   - `flutter test`: 97+ unit & widget tests pass (Auth, Tokens, AI Chat, AI Project Creation, Investor Module, Collaboration Requests).
   - Only `export_screens_golden_test.dart` has golden image mismatches (expected for golden export tests).
3. **Android Release Build Setting:**
   - Enable `isMinifyEnabled = true` and ProGuard rules in `android/app/build.gradle.kts` for production APK/AAB builds.
