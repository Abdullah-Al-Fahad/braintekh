# DiasporaVest / Damani AI: Social Authentication (Google & Apple) Backend Integration Specification

This document provides the backend engineering team with the complete technical specification, architectural lifecycle, cryptographic token verification procedures, database schema recommendations, and production-ready reference implementations to set up **Google Sign-In** and **Apple Sign-In** for this project.

The mobile client architecture directly adapts the proven, working social sign-in implementation from the reference production project (`v2scorelivepro`), customized for this project's **Django REST Framework (DRF)**, **SimpleJWT**, **Clean Architecture**, and **Dual-Persona (Investor / Sponsor) Lifecycle**.

---

## 1. Executive Summary & Authentication Flow

### 1.1 Dual-Persona Architecture Context
Users on DiasporaVest / Damani AI operate under two primary roles: **INVESTOR** or **SPONSOR**:
1. **First-time Authentication**:
   - When a user signs in via Google or Apple for the first time, an account is created with `is_email_verified: true` and `role: "NONE"`.
   - The Flutter mobile client checks `role`. If `role == "NONE"`, it routes the user to `/role-selection` (`ChooseTypeScreen`) where the user picks **Investor** or **Sponsor**, starting the onboarding sequence (`POST /api/v1/profiles/set-role/`).
2. **Returning Authenticated Users**:
   - When an existing user signs in whose role is already established (`"INVESTOR"` or `"SPONSOR"`), the backend returns their active role.
   - The mobile client immediately routes directly to the main dashboard (`/home`).
3. **Account Linking**:
   - If an account already exists with the same email (e.g. previously registered via email/password), the backend securely links the `google_id` or `apple_id` to the existing user without duplicate account creation.

### 1.2 Authentication Lifecycle Diagram

```
[Flutter Mobile App]              [Google / Apple SDK]             [Backend API (DRF)]
         │                                 │                                │
         ├──── Tap "Continue with Google" ─►                                │
         │     or "Continue with Apple"    │                                │
         │                                 │                                │
         │◄─── Returns id_token (+ name) ──┤                                │
         │                                                                  │
         ├──── POST /api/v1/auth/google/ (id_token) ───────────────────────►│
         │     or POST /api/v1/auth/apple/ (id_token, user)                 │
         │                                                                  │
         │                                              [1. Verify JWT Signature via JWKS]
         │                                              [2. Validate aud, iss, exp claims]
         │                                              [3. Lookup by Provider ID or Email]
         │                                              [4. Link Account or Create User]
         │                                              [5. Generate SimpleJWT Tokens]
         │                                                                  │
         │◄─── 200 OK {status, access, refresh, role, user} ────────────────┤
         │                                                                  │
         ├── If role == "NONE" ────► Route to /role-selection               │
         └── If role != "NONE" ────► Route to /home (Dashboard)             │
```

---

## 2. Project Identifiers & Console Setup Requirements

The backend developer and DevOps/Firebase administrators must ensure the credentials match these exact project configurations:

| Parameter | Value | Location in Flutter Project |
|---|---|---|
| **Android Application ID** | `com.braintekh.diafi` | `android/app/build.gradle.kts` |
| **Android Namespace** | `com.braintekh.diafi` | `android/app/build.gradle.kts` |
| **iOS Bundle Identifier** | `com.braintekh.diafi` | `ios/Runner.xcodeproj/project.pbxproj` |
| **Firebase Project ID** | `damini-ai` | `lib/firebase_options.dart` / `.env` |
| **Firebase Project Number** | `1003008036989` | `android/app/google-services.json` |
| **Storage Bucket** | `damini-ai.firebasestorage.app` | `android/app/google-services.json` |
| **Base API URL** | `https://clubby-andy-irksomely.ngrok-free.dev` | `lib/core/constants/api_endpoints.dart` |
| **Auth API Prefix** | `/api/v1/auth/` | Consistent across all auth endpoints |

---

### 2.1 Google Cloud & Firebase Console Configuration

To enable Google Sign-In, the following three configurations must be created in the **Google Cloud Console / Firebase Console** under project `damini-ai`:

#### Step 1: Create OAuth 2.0 Web Client ID (Backend Server Client ID)
1. Go to **Google Cloud Console** > **APIs & Services** > **Credentials**.
2. Click **Create Credentials** > **OAuth client ID**.
3. Select Application type: **Web application**.
4. Name: `Damani AI Web Backend Client`.
5. Authorized redirect URIs: Leave empty or add backend auth callback URL if needed.
6. **Key Deliverable for Flutter Team**:
   - Provide this Web Client ID (e.g., `1003008036989-xxxxxxxxxxxxxxxx.apps.googleusercontent.com`) to the Flutter team to set as `GOOGLE_SERVER_CLIENT_ID` in `.env`.
   - The backend uses this Web Client ID to verify the `aud` claim in incoming Google ID tokens.

#### Step 2: Register Android App & SHA-1 / SHA-256 Fingerprints
> [!WARNING]
> **Common Android Pitfall**: If SHA-1 is not registered in Firebase, Google Sign-In on Android will fail immediately with `ApiException: 10` (Developer Error).
1. Run the keytool command to extract the development SHA-1 and SHA-256:
   ```bash
   # Windows PowerShell:
   keytool -list -v -keystore "$env:USERPROFILE\.android\debug.keystore" -alias androiddebugkey -storepass android -keypass android
   
   # macOS / Linux:
   keytool -list -v -keystore ~/.android/debug.keystore -alias androiddebugkey -storepass android -keypass android
   ```
2. In **Firebase Console** > **Project Settings** > **Your apps** > Select Android app (`com.braintekh.diafi`):
   - Add the **SHA-1** fingerprint.
   - Add the **SHA-256** fingerprint.
   - Also add the release keystore SHA-1/SHA-256 when building release APKs/AABs.
3. Download the updated `google-services.json` (which will now contain the populated `oauth_client` array) and replace `android/app/google-services.json`.

#### Step 3: Configure iOS in Firebase & Apple Developer
1. In Firebase Console, create the iOS app with Bundle ID `com.braintekh.diafi`.
2. Download `GoogleService-Info.plist` and place it in `ios/Runner/GoogleService-Info.plist`.
3. Locate `REVERSED_CLIENT_ID` inside `GoogleService-Info.plist` (e.g. `com.googleusercontent.apps.1003008036989-xxxxxx`).
4. In `ios/Runner/Info.plist`, ensure `CFBundleURLTypes` includes this URL scheme:
   ```xml
   <key>CFBundleURLTypes</key>
   <array>
       <dict>
           <key>CFBundleTypeRole</key>
           <string>Editor</string>
           <key>CFBundleURLSchemes</key>
           <array>
               <string>com.googleusercontent.apps.1003008036989-xxxxxx</string>
           </array>
       </dict>
   </array>
   ```

---

### 2.2 Apple Developer Console Configuration

#### Step 1: Enable Sign in with Apple on App ID
1. Log into **Apple Developer Portal** > **Certificates, Identifiers & Profiles** > **Identifiers**.
2. Select App ID: `com.braintekh.diafi`.
3. Check the **Sign In with Apple** capability (Edit > Primary App ID).

#### Step 2: Create Apple Private Key (`.p8`) for Backend
To perform token revocation (mandated by App Store Review Guideline 5.1.1(v) for apps offering account deletion) and server-to-server token refresh:
1. Go to **Keys** > **Create a key** (+).
2. Key Name: `Damani AI Sign In with Apple Key`.
3. Check **Sign in with Apple** > Click **Configure** > Select Primary App ID `com.braintekh.diafi`.
4. Download the `.p8` private key file (e.g., `AuthKey_ABC123XYZ.p8`).
5. Record:
   - **Apple Team ID**: 10-character Team ID (found in top-right of developer portal).
   - **Key ID (`kid`)**: 10-character Key ID (e.g. `ABC123XYZ`).
   - **Client ID**: `com.braintekh.diafi` (for iOS) or Services ID (for Android/Web).

---

## 3. API Endpoints Specification

### 3.1 Google Authentication Endpoint

- **Endpoint:** `POST /api/v1/auth/google/`
- **Authentication:** Public (No Bearer token required)
- **Headers:** `Content-Type: application/json`

#### Request Payload
```json
{
  "id_token": "eyJhbGciOiJSUzI1NiIsImtpZCI6IjFkOGQ1... (Google OpenID Connect JWT)"
}
```

#### Verification Steps on Backend:
1. Decode and verify the JWT signature against Google's public JWKS certificates:
   `https://www.googleapis.com/oauth2/v3/certs`
2. Validate claims:
   - `iss`: Must be `"accounts.google.com"` or `"https://accounts.google.com"`.
   - `aud`: Must match your backend's **Google Web Client ID** (`GOOGLE_WEB_CLIENT_ID`).
   - `exp`: Must be in the future (token is unexpired).
3. Extract verified user profile claims:
   - `sub`: Unique Google User ID (immutable string; save to `user.google_id`).
   - `email`: Verified email address (`user.email`).
   - `email_verified`: Boolean (true for Google).
   - `given_name`: First name (`user.first_name`).
   - `family_name`: Last name (`user.last_name`).
   - `name`: Full display name (`user.full_name`).
   - `picture`: Profile picture URL (optional; can be saved to user profile).

---

### 3.2 Apple Authentication Endpoint

- **Endpoint:** `POST /api/v1/auth/apple/`
- **Authentication:** Public (No Bearer token required)
- **Headers:** `Content-Type: application/json`

#### Request Payload
```json
{
  "id_token": "eyJraWQiOiI4NkQ4O... (Apple identityToken JWT)",
  "user": {
    "name": {
      "firstName": "John",
      "lastName": "Doe"
    }
  }
}
```

> [!IMPORTANT]
> **Apple First-Time Only Name Behavior**:
> Apple provides the user's name (`user.name.firstName`, `user.name.lastName`) **ONLY ONCE**—during the initial authorization!
> On subsequent logins, `user` will be omitted or `null`.
> The backend **must** capture and save the name on the first login. On future logins, identify the user via the `sub` claim inside the verified `id_token`.
> If `user.name` is null on registration, fallback to the prefix of the email address (e.g. `john` from `john@gmail.com`).

#### Verification Steps on Backend:
1. Extract unverified header `kid` from `id_token`.
2. Retrieve the public key matching `kid` from Apple's JWKS:
   `https://appleid.apple.com/auth/keys`
3. Verify signature using RS256 algorithm.
4. Validate claims:
   - `iss`: Must be `"https://appleid.apple.com"`.
   - `aud`: Must match the iOS Bundle Identifier: `"com.braintekh.diafi"`.
   - `exp`: Must be in the future.
5. Extract user claims:
   - `sub`: Unique Apple Subject ID (immutable identifier; save to `user.apple_id`).
   - `email`: User's real or private relay email (`...@privaterelay.appleid.com`).
   - `email_verified`: Set to `true` (Apple verifies emails).

---

## 4. Response Schemas (Matching Flutter Client)

The Flutter mobile application (`LoginRepositoryImpl` and `UserModel` in `lib/views/auth/login/models/login_request_model.dart`) expects responses in the exact format below.

### 4.1 Success Response (`200 OK` or `201 Created`)

```json
{
  "status": "success",
  "message": "Login successful",
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNjg...",
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6MTY4...",
  "role": "NONE",
  "user": {
    "id": 42,
    "first_name": "John",
    "last_name": "Doe",
    "full_name": "John Doe",
    "email": "johndoe@gmail.com",
    "role": "NONE",
    "is_email_verified": true,
    "push_notifications_enabled": false,
    "subscription_tier": "FREE"
  }
}
```

#### Field Specifications:
- `access`: Standard Django SimpleJWT access token string. Saved to secure storage as `access`.
- `refresh`: Standard Django SimpleJWT refresh token string. Saved to secure storage as `refresh`.
- `role`: User's current role string (`"NONE"`, `"INVESTOR"`, or `"SPONSOR"`):
  - **New Users**: Must be `"NONE"`. Mobile app automatically navigates to `/role-selection`.
  - **Returning Users with completed onboarding**: `"INVESTOR"` or `"SPONSOR"`. Mobile app navigates directly to `/home`.
- `user.id`: Integer database ID.
- `user.is_email_verified`: Set to `true`.
- `user.push_notifications_enabled`: Boolean (defaults to `false`).
- `user.subscription_tier`: Defaults to `"FREE"`.

---

### 4.2 Error Responses

#### Invalid or Expired Social Token (`400 Bad Request` or `401 Unauthorized`)
```json
{
  "status": "error",
  "message": "Invalid or expired social token."
}
```

#### Missing Token (`400 Bad Request`)
```json
{
  "status": "error",
  "message": "id_token is required.",
  "errors": {
    "id_token": [
      "This field is required."
    ]
  }
}
```

---

## 5. Account Linking & Security Edge Cases

1. **Existing Email Account Linking**:
   - If a user previously registered using email/password (`test@example.com`) and later taps "Continue with Google" or "Continue with Apple" with the same email:
   - The backend checks if `User.objects.filter(email__iexact=email).exists()`.
   - If found, link `google_id` or `apple_id` to the existing account, preserve existing role, and generate new JWT tokens.
2. **Apple Private Relay Emails**:
   - When users choose "Hide My Email", Apple provides a proxied address (e.g., `s9df87s6df@privaterelay.appleid.com`).
   - Always query by `apple_id` (`sub`) first before attempting an email search.
3. **Unusable Password**:
   - Social accounts must have an unusable password set (`user.set_unusable_password()`), preventing empty-password login attacks.
4. **Account Deletion & Apple Revocation (App Store Requirement)**:
   - When `POST /api/v1/users/delete-account/` is invoked for an Apple user, the backend should call Apple's revocation endpoint:
     `POST https://appleid.apple.com/auth/oauth2/revoke`
     Parameters: `client_id`, `client_secret` (generated using `.p8` key), `token`, `token_type_hint=access_token`.

---

## 6. Django REST Framework Implementation (Production Reference Code)

### 6.1 Requirements
Install the necessary Python packages:
```bash
pip install google-auth pyjwt[crypto] requests djangorestframework-simplejwt
```

---

### 6.2 Settings Configuration (`settings.py`)

```python
# settings.py
GOOGLE_WEB_CLIENT_ID = "1003008036989-xxxxxxxxxxxxxxxx.apps.googleusercontent.com"
APPLE_BUNDLE_ID = "com.braintekh.diafi"
APPLE_TEAM_ID = "XXXXXXXXXX"
APPLE_KEY_ID = "YYYYYYYYYY"
```

---

### 6.3 Database Model (`users/models.py`)

```python
# users/models.py
from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    class RoleChoices(models.TextChoices):
        NONE = 'NONE', 'None'
        INVESTOR = 'INVESTOR', 'Investor'
        SPONSOR = 'SPONSOR', 'Sponsor'

    email = models.EmailField(unique=True)
    role = models.CharField(
        max_length=20,
        choices=RoleChoices.choices,
        default=RoleChoices.NONE,
    )
    is_email_verified = models.BooleanField(default=False)
    push_notifications_enabled = models.BooleanField(default=False)
    subscription_tier = models.CharField(max_length=20, default='FREE')

    # Social Provider Unique Identifiers
    google_id = models.CharField(max_length=255, null=True, blank=True, unique=True, db_index=True)
    apple_id = models.CharField(max_length=255, null=True, blank=True, unique=True, db_index=True)

    @property
    def full_name(self):
        name = f"{self.first_name} {self.last_name}".strip()
        return name if name else (self.username or self.email)
```

---

### 6.4 Social Token Verification Service (`services/social_auth.py`)

Using `jwt.PyJWKClient` provides automatic key caching and eliminates redundant network calls on each authentication request:

```python
# services/social_auth.py
import jwt
from jwt import PyJWKClient
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from django.conf import settings
from rest_framework.exceptions import AuthenticationFailed

class SocialAuthService:
    # PyJWKClient with caching enabled prevents rate-limiting and reduces latency
    _apple_jwk_client = PyJWKClient(
        "https://appleid.apple.com/auth/keys",
        cache_keys=True,
        max_cached_keys=16
    )

    @classmethod
    def verify_google_token(cls, token_str: str) -> dict:
        """
        Validates Google ID Token against Google JWKS.
        """
        try:
            id_info = id_token.verify_oauth2_token(
                token_str,
                google_requests.Request(),
                settings.GOOGLE_WEB_CLIENT_ID
            )

            if id_info.get('iss') not in ['accounts.google.com', 'https://accounts.google.com']:
                raise AuthenticationFailed('Invalid Google token issuer.')

            return {
                'sub': id_info['sub'],
                'email': id_info.get('email'),
                'first_name': id_info.get('given_name', ''),
                'last_name': id_info.get('family_name', ''),
                'picture': id_info.get('picture', ''),
            }
        except ValueError as e:
            raise AuthenticationFailed(f'Invalid Google token: {str(e)}')

    @classmethod
    def verify_apple_token(cls, token_str: str) -> dict:
        """
        Validates Apple identityToken against Apple JWKS.
        """
        try:
            # 1. Fetch signing key from cached Apple JWKS
            signing_key = cls._apple_jwk_client.get_signing_key_from_jwt(token_str)

            # 2. Decode & verify claims
            payload = jwt.decode(
                token_str,
                signing_key.key,
                algorithms=['RS256'],
                audience=settings.APPLE_BUNDLE_ID,
                issuer="https://appleid.apple.com"
            )

            return {
                'sub': payload['sub'],
                'email': payload.get('email'),
            }
        except Exception as e:
            raise AuthenticationFailed(f'Invalid Apple token: {str(e)}')
```

---

### 6.5 Serializers & Views (`api/views/auth_views.py`)

```python
# api/views/auth_views.py
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.db import transaction
from services.social_auth import SocialAuthService

User = get_user_model()

class GoogleAuthSerializer(serializers.Serializer):
    id_token = serializers.CharField(required=True, trim_whitespace=True)

class AppleAuthSerializer(serializers.Serializer):
    id_token = serializers.CharField(required=True, trim_whitespace=True)
    user = serializers.DictField(required=False, allow_null=True)

def build_auth_payload(user: User) -> dict:
    refresh = RefreshToken.for_user(user)
    return {
        "status": "success",
        "message": "Login successful",
        "access": str(refresh.access_token),
        "refresh": str(refresh),
        "role": user.role,
        "user": {
            "id": user.id,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "full_name": user.full_name,
            "email": user.email,
            "role": user.role,
            "is_email_verified": user.is_email_verified,
            "push_notifications_enabled": user.push_notifications_enabled,
            "subscription_tier": user.subscription_tier,
        }
    }

class GoogleLoginView(APIView):
    permission_classes = []

    def post(self, request):
        serializer = GoogleAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token_str = serializer.validated_data['id_token']
        profile = SocialAuthService.verify_google_token(token_str)

        email = profile.get('email')
        google_id = profile.get('sub')

        with transaction.atomic():
            # 1. Match by google_id
            user = User.objects.filter(google_id=google_id).first()

            # 2. Match by email (Account Linking)
            if not user and email:
                user = User.objects.filter(email__iexact=email).first()
                if user:
                    user.google_id = google_id
                    user.is_email_verified = True
                    user.save(update_fields=['google_id', 'is_email_verified'])

            # 3. Create new user
            if not user:
                username = email or f"google_{google_id}"
                user = User(
                    username=username,
                    email=email or f"{google_id}@google.com",
                    first_name=profile.get('first_name', ''),
                    last_name=profile.get('last_name', ''),
                    google_id=google_id,
                    is_email_verified=True,
                    role=User.RoleChoices.NONE,
                )
                user.set_unusable_password()
                user.save()

        return Response(build_auth_payload(user), status=status.HTTP_200_OK)


class AppleLoginView(APIView):
    permission_classes = []

    def post(self, request):
        serializer = AppleAuthSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token_str = serializer.validated_data['id_token']
        user_meta = serializer.validated_data.get('user') or {}
        profile = SocialAuthService.verify_apple_token(token_str)

        apple_id = profile.get('sub')
        email = profile.get('email')

        # Extract name if present (Apple only sends this on first sign in)
        name_obj = user_meta.get('name', {}) if isinstance(user_meta, dict) else {}
        first_name = name_obj.get('firstName', '')
        last_name = name_obj.get('lastName', '')

        with transaction.atomic():
            # 1. Match by apple_id
            user = User.objects.filter(apple_id=apple_id).first()

            # 2. Match by email (Account Linking)
            if not user and email:
                user = User.objects.filter(email__iexact=email).first()
                if user:
                    user.apple_id = apple_id
                    user.is_email_verified = True
                    user.save(update_fields=['apple_id', 'is_email_verified'])

            # 3. Create new user
            if not user:
                default_name = email.split('@')[0] if email else "User"
                username = email or f"apple_{apple_id}"
                user = User(
                    username=username,
                    email=email or f"{apple_id}@privaterelay.appleid.com",
                    first_name=first_name or default_name,
                    last_name=last_name or "",
                    apple_id=apple_id,
                    is_email_verified=True,
                    role=User.RoleChoices.NONE,
                )
                user.set_unusable_password()
                user.save()

        return Response(build_auth_payload(user), status=status.HTTP_200_OK)
```

---

### 6.6 URL Patterns (`api/urls.py`)

```python
# api/urls.py
from django.urls import path
from api.views.auth_views import GoogleLoginView, AppleLoginView

urlpatterns = [
    # Existing auth endpoints
    # path('api/v1/auth/login/', LoginView.as_view(), name='login'),
    # path('api/v1/auth/register/', RegisterView.as_view(), name='register'),

    # Social authentication endpoints
    path('api/v1/auth/google/', GoogleLoginView.as_view(), name='auth-google'),
    path('api/v1/auth/apple/', AppleLoginView.as_view(), name='auth-apple'),
]
```

---

## 7. Node.js / Express Alternative Reference

If the backend architecture is Node.js / TypeScript, use the following equivalent implementation:

```typescript
import { OAuth2Client } from 'google-auth-library';
import jwt from 'jsonwebtoken';
import jwksClient from 'jwks-rsa';

const googleClient = new OAuth2Client(process.env.GOOGLE_WEB_CLIENT_ID);

// 1. Google ID Token Verification
export async function verifyGoogleToken(idToken: string) {
  const ticket = await googleClient.verifyIdToken({
    idToken,
    audience: process.env.GOOGLE_WEB_CLIENT_ID,
  });
  return ticket.getPayload(); // { sub, email, given_name, family_name, picture }
}

// 2. Apple identityToken Verification
const appleJwks = jwksClient({
  jwksUri: 'https://appleid.apple.com/auth/keys',
  cache: true,
  rateLimit: true,
});

export async function verifyAppleToken(idToken: string) {
  const decodedHeader = jwt.decode(idToken, { complete: true });
  if (!decodedHeader?.header?.kid) throw new Error('Missing kid in Apple token header');

  const key = await appleJwks.getSigningKey(decodedHeader.header.kid);
  const signingKey = key.getPublicKey();

  return jwt.verify(idToken, signingKey, {
    audience: 'com.braintekh.diafi',
    issuer: 'https://appleid.apple.com',
    algorithms: ['RS256'],
  }) as { sub: string; email?: string };
}
```

---

## 8. Mobile Client Integration Blueprint (Flutter)

For full context and seamless collaboration, this is how the Flutter client connects to these endpoints (adapting `v2scorelivepro` into `Braintech` Clean Architecture):

### 8.1 Dependencies Added to `pubspec.yaml`
```yaml
dependencies:
  google_sign_in: ^7.2.0
  sign_in_with_apple: ^8.1.0
```

### 8.2 Endpoints in `lib/core/constants/api_endpoints.dart`
```dart
class ApiEndpoints {
  // ...
  static const String googleLogin = "/api/v1/auth/google/";
  static const String appleLogin = "/api/v1/auth/apple/";
}
```

### 8.3 Google Auth Service (`lib/core/services/google_auth_service.dart`)
```dart
import 'package:flutter_dotenv/flutter_dotenv.dart';
import 'package:google_sign_in/google_sign_in.dart';
import '../constants/api_endpoints.dart';
import 'api_service.dart';

class GoogleAuthService {
  final ApiService apiService;
  GoogleSignIn get _googleSignIn => GoogleSignIn.instance;

  GoogleAuthService(this.apiService);

  Future<Map<String, dynamic>?> signIn() async {
    await _googleSignIn.initialize(
      serverClientId: dotenv.env['GOOGLE_SERVER_CLIENT_ID'],
    );
    final GoogleSignInAccount googleUser = await _googleSignIn.authenticate(
      scopeHint: ['email', 'profile'],
    );
    final GoogleSignInAuthentication googleAuth = googleUser.authentication;
    final String? idToken = googleAuth.idToken;

    if (idToken == null) return null;

    final response = await apiService.post(
      ApiEndpoints.googleLogin,
      data: {'id_token': idToken},
      requireAuth: false,
    );
    return response.data is Map<String, dynamic> ? response.data : null;
  }
}
```

### 8.4 Apple Auth Service (`lib/core/services/apple_auth_service.dart`)
```dart
import 'package:sign_in_with_apple/sign_in_with_apple.dart';
import '../constants/api_endpoints.dart';
import 'api_service.dart';

class AppleAuthService {
  final ApiService apiService;

  AppleAuthService(this.apiService);

  Future<Map<String, dynamic>?> signIn() async {
    final credential = await SignInWithApple.getAppleIDCredential(
      scopes: [
        AppleIDAuthorizationScopes.email,
        AppleIDAuthorizationScopes.fullName,
      ],
    );

    final String? idToken = credential.identityToken;
    if (idToken == null) return null;

    final body = {
      'id_token': idToken,
      if (credential.givenName != null || credential.familyName != null)
        'user': {
          'name': {
            if (credential.givenName != null) 'firstName': credential.givenName,
            if (credential.familyName != null) 'lastName': credential.familyName,
          }
        }
    };

    final response = await apiService.post(
      ApiEndpoints.appleLogin,
      data: body,
      requireAuth: false,
    );
    return response.data is Map<String, dynamic> ? response.data : null;
  }
}
```

### 8.5 Social Auth Buttons (`SocialAuthSection` in `lib/views/auth/widgets/social_auth_section.dart`)
The `Continue with Google` and `Continue with Apple` buttons invoke these services, parse the returned response through `LoginRepositoryImpl`, persist the tokens to `StorageService`, and navigate according to `role`:
- If `role == "NONE"` -> Navigate to `/role-selection`.
- If `role == "INVESTOR"` or `"SPONSOR"` -> Navigate to `/home`.

---

## 9. Backend Developer Verification Checklist

- [ ] **Google Web Client ID**: Created in Google Cloud Console (`damini-ai`) and shared with mobile developer.
- [ ] **Android SHA-1 & SHA-256**: Added to Firebase project settings for `com.braintekh.diafi`, and updated `google-services.json` provided to Flutter team.
- [ ] **iOS Configuration**: `com.braintekh.diafi` registered in Apple Developer portal with "Sign In with Apple" enabled; `GoogleService-Info.plist` generated and provided to Flutter team.
- [ ] **Google Auth Endpoint**: `POST /api/v1/auth/google/` implemented and verified with Google JWKS signature validation and `aud` matching Web Client ID.
- [ ] **Apple Auth Endpoint**: `POST /api/v1/auth/apple/` implemented with cached Apple JWKS (`PyJWKClient`) and `aud` matching `com.braintekh.diafi`.
- [ ] **Role Lifecycle**: Sets `role: "NONE"` for brand new users, prompting `/role-selection` routing on client.
- [ ] **Returning Users**: Returns user's actual role (`"INVESTOR"` or `"SPONSOR"`) on re-login.
- [ ] **Account Linking**: Successfully links `google_id` / `apple_id` when email matches an existing email/password account.
- [ ] **Token Structure**: Returns standard SimpleJWT `access` and `refresh` tokens with full `user` object conforming to `UserModel`.
