# Save Profile & Saved Profiles Tab — Backend API Specification

This document details the backend requirements for the **Save Profile (Bookmark)** flow, **Saved Profiles Tab**, and **Public Profile Integration** for the mobile application.

---

## 1. Overview & Business Flow

1. **Save/Bookmark Toggle**:
   - Any authenticated user (Sponsor, Investor, etc.) can save/bookmark another user's public profile for quick access.
   - Hitting `POST /api/v1/users/<id>/save/` toggles the save state (saves if not saved, removes if already saved).
   - **Self-Save Restriction**: A user cannot save their own profile. Returning HTTP 400 with a clear error message is required.
2. **Saved Profiles List**:
   - Accessible via `GET /api/v1/users/saved/`.
   - Returns a paginated list of all profiles the authenticated user has saved.
   - Supports searching by user's full name, company name, or designation (`?search=...`).
   - Supports ordering by newest saved date, oldest, or alphabetical by name (`?ordering=-created_at|created_at|name|-name`).
3. **Public Profile Query**:
   - When fetching a public profile via `GET /api/v1/users/<id>/`, the response includes `is_saved` (boolean) indicating whether the current requesting user has saved this profile.

---

## 2. Database Schema (Django Reference)

### Model: `SavedProfile`

```python
# models.py
from django.db import models
from django.conf import settings

class SavedProfile(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='saved_profiles',
        help_text="The user who bookmarked the profile"
    )
    saved_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='saved_by_users',
        help_text="The profile/user that was bookmarked"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'user_saved_profiles'
        unique_together = ('user', 'saved_user')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} saved {self.saved_user.email}"
```

---

## 3. API Endpoints

### 3.1. Toggle Save Profile
- **Endpoint**: `POST /api/v1/users/<id>/save/`
- **Authentication**: Required (`Bearer <token>`)
- **Path Parameter**:
  - `id`: Target user's primary key / ID (e.g., `42`).

#### Logic:
1. Verify `request.user` is authenticated.
2. If `request.user.id == target_user.id`, return **400 Bad Request** (`"You cannot save your own profile."`).
3. Check if a `SavedProfile` record exists for `(user=request.user, saved_user=target_user)`:
   - If **exists**: Delete the record → return `is_saved: false`.
   - If **does not exist**: Create the record → return `is_saved: true`.

#### Success Response (200 OK / 201 Created):
```json
{
  "success": true,
  "message": "Profile saved successfully.",
  "is_saved": true,
  "user_id": 42
}
```

#### Success Response when Unsaved (200 OK):
```json
{
  "success": true,
  "message": "Profile removed from saved items.",
  "is_saved": false,
  "user_id": 42
}
```

#### Error Responses:
- **400 Bad Request** (Self-save attempt):
  ```json
  {
    "detail": "You cannot save your own profile."
  }
  ```
- **401 Unauthorized**:
  ```json
  {
    "detail": "Authentication credentials were not provided."
  }
  ```
- **404 Not Found** (Target user doesn't exist or is inactive):
  ```json
  {
    "detail": "User not found."
  }
  ```

---

### 3.2. List Saved Profiles
- **Endpoint**: `GET /api/v1/users/saved/`
- **Authentication**: Required (`Bearer <token>`)
- **Query Parameters**:
  - `search` *(optional, string)*: Filter by target user's first name, last name, company, or designation.
  - `ordering` *(optional, string)*:
    - `-created_at` (default, Newest first)
    - `created_at` (Oldest first)
    - `name` / `first_name` (A to Z)
    - `-name` / `-first_name` (Z to A)
  - `page` *(optional, int)*: Page number.
  - `page_size` *(optional, int)*: Page size (default 20).

#### Response (200 OK):
```json
{
  "count": 2,
  "next": null,
  "previous": null,
  "results": [
    {
      "id": "1",
      "user_id": "42",
      "name": "Sarah Jenkins",
      "title": "Angel Investor",
      "company": "Vanguard Investments",
      "avatar_url": "https://storage.example.com/avatars/sarah.jpg",
      "location": "San Francisco, CA",
      "role": "INVESTOR",
      "is_saved": true,
      "created_at": "2026-10-06T11:42:00Z"
    },
    {
      "id": "2",
      "user_id": "18",
      "name": "Marcus Vance",
      "title": "Venture Partner",
      "company": "Apex Tech Ventures",
      "avatar_url": "https://storage.example.com/avatars/marcus.jpg",
      "location": "Austin, TX",
      "role": "INVESTOR",
      "is_saved": true,
      "created_at": "2026-10-05T09:15:00Z"
    }
  ]
}
```

*Note: The mobile app's model is designed to accept either the standard Django REST Framework pagination schema (`{count, results: [...]}`) or wrapped (`{data: {results: [...]}}` / `{data: [...]}`).*

---

### 3.3. Public Profile Detail (Enriched)
- **Endpoint**: `GET /api/v1/users/<id>/` (or `GET /api/v1/profiles/<id>/`)
- **Authentication**: Required (`Bearer <token>`)

#### Response (200 OK):
```json
{
  "id": 42,
  "first_name": "Sarah",
  "last_name": "Jenkins",
  "email": "sarah@vanguard.com",
  "role": "INVESTOR",
  "phone": "+1 555-0199",
  "is_verified": true,
  "is_saved": true,
  "is_own_profile": false,
  "profile": {
    "title": "Angel Investor",
    "company": "Vanguard Investments",
    "avatar_url": "https://storage.example.com/avatars/sarah.jpg",
    "location": "San Francisco, CA",
    "country": "United States",
    "website": "https://vanguard.com",
    "bio": "Early-stage angel investor focusing on fintech and sustainable tech innovations."
  }
}
```

---

## 4. Reference Django Implementation

```python
# views.py
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.generics import ListAPIView
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from django.db.models import Q

from .models import SavedProfile
from .serializers import SavedProfileSerializer

User = get_user_model()

class ToggleSaveProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, id):
        target_user = get_object_or_404(User, id=id, is_active=True)

        # 1. Validation: Prevent self-saving
        if target_user.id == request.user.id:
            return Response(
                {"detail": "You cannot save your own profile."},
                status=status.status.HTTP_400_BAD_REQUEST
            )

        # 2. Toggle Bookmark
        saved_instance = SavedProfile.objects.filter(
            user=request.user,
            saved_user=target_user
        ).first()

        if saved_instance:
            saved_instance.delete()
            return Response({
                "success": True,
                "message": "Profile removed from saved items.",
                "is_saved": False,
                "user_id": target_user.id
            }, status=status.HTTP_200_OK)
        else:
            SavedProfile.objects.create(
                user=request.user,
                saved_user=target_user
            )
            return Response({
                "success": True,
                "message": "Profile saved successfully.",
                "is_saved": True,
                "user_id": target_user.id
            }, status=status.HTTP_201_CREATED)


class SavedProfilesListView(ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = SavedProfileSerializer

    def get_queryset(self):
        qs = SavedProfile.objects.filter(
            user=self.request.user,
            saved_user__is_active=True
        ).select_related('saved_user', 'saved_user__profile')

        # Search
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(
                Q(saved_user__first_name__icontains=search) |
                Q(saved_user__last_name__icontains=search) |
                Q(saved_user__profile__company__icontains=search) |
                Q(saved_user__profile__title__icontains=search)
            )

        # Ordering
        ordering = self.request.query_params.get('ordering', '-created_at')
        if ordering == 'name':
            qs = qs.order_by('saved_user__first_name', 'saved_user__last_name')
        elif ordering == '-name':
            qs = qs.order_by('-saved_user__first_name', '-saved_user__last_name')
        elif ordering == 'created_at':
            qs = qs.order_by('created_at')
        else:
            qs = qs.order_by('-created_at')

        return qs
```

```python
# serializers.py
from rest_framework import serializers
from .models import SavedProfile

class SavedProfileSerializer(serializers.ModelSerializer):
    user_id = serializers.CharField(source='saved_user.id')
    name = serializers.SerializerMethodField()
    title = serializers.SerializerMethodField()
    company = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()
    role = serializers.CharField(source='saved_user.role', default='INVESTOR')
    is_saved = serializers.BooleanField(default=True)

    class Meta:
        model = SavedProfile
        fields = [
            'id',
            'user_id',
            'name',
            'title',
            'company',
            'avatar_url',
            'location',
            'role',
            'is_saved',
            'created_at'
        ]

    def get_name(self, obj):
        user = obj.saved_user
        full_name = f"{user.first_name} {user.last_name}".strip()
        return full_name if full_name else getattr(user, 'name', 'User')

    def get_title(self, obj):
        profile = getattr(obj.saved_user, 'profile', None)
        return getattr(profile, 'title', '') or getattr(profile, 'designation', 'Member')

    def get_company(self, obj):
        profile = getattr(obj.saved_user, 'profile', None)
        return getattr(profile, 'company', '') or getattr(profile, 'legal_company_name', '')

    def get_avatar_url(self, obj):
        profile = getattr(obj.saved_user, 'profile', None)
        photo = getattr(profile, 'profile_photo', None) or getattr(obj.saved_user, 'avatar', None)
        return photo.url if photo and hasattr(photo, 'url') else (str(photo) if photo else '')

    def get_location(self, obj):
        profile = getattr(obj.saved_user, 'profile', None)
        city = getattr(profile, 'city', '')
        country = getattr(profile, 'country', '')
        if city and country:
            return f"{city}, {country}"
        return city or country or "Not specified"
```

```python
# urls.py
from django.urls import path
from .views import ToggleSaveProfileView, SavedProfilesListView

urlpatterns = [
    path('api/v1/users/<int:id>/save/', ToggleSaveProfileView.as_view(), name='toggle-save-profile'),
    path('api/v1/users/saved/', SavedProfilesListView.as_view(), name='saved-profiles-list'),
]
```

---

## 5. Edge Cases Handled

1. **Self-Save Attempt**:
   - Status 400 Bad Request returned if `request.user.id == target_user.id`.
   - Frontend UI also hides the bookmark button when `isOwnProfile == true`.
2. **Target User Deleted / Deactivated**:
   - `saved_user__is_active=True` filter prevents deactivated users from showing up in the list.
   - Foreign key has `on_delete=CASCADE` to clean up saved entries automatically if an account is deleted.
3. **Idempotent / Race Conditions**:
   - `unique_together = ('user', 'saved_user')` guarantees no duplicate records can ever be inserted into the database.
4. **Invalid / Missing Avatar URLs**:
   - Serializer guarantees non-null fallback string or empty string; frontend includes safe fallback rendering to prevent mobile crashes.
