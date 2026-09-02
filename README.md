# Damani AI — Backend API

A production-ready Django REST Framework backend for the Damani AI / Synvest platform, powering the authentication, onboarding, and compliance workflows for Investors and Sponsors.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | Django 6.1 + Django REST Framework 3.18 |
| Auth | JWT via `djangorestframework-simplejwt` (with blacklisting) |
| Env Config | `django-environ` |
| CORS | `django-cors-headers` |
| Image Handling | `Pillow` |

---

## Project Structure

```
Braintekh/
├── config/
│   ├── settings.py        # All settings (env-driven)
│   ├── urls.py            # Root URL config (versioned: /api/v1/)
│   ├── wsgi.py
│   └── asgi.py
├── core/                  # Shared base — no business logic here
│   ├── models.py          # TimeStampedModel (abstract base for all models)
│   ├── exceptions.py      # Global custom DRF exception handler
│   ├── responses.py       # Standardized API response helpers
│   ├── permissions.py     # IsEmailVerified, IsInvestor, IsSponsor
│   └── throttles.py       # AuthRateThrottle (5/min on auth endpoints)
├── users/                 # Custom User model (email-based, no username)
│   ├── models.py          # User, RoleChoices, UserManager
│   ├── serializers.py     # UserDetailsSerializer
│   └── admin.py
├── authentication/        # Registration, OTP, login, password reset
│   ├── models.py          # OTPRecord (cryptographically secure, indexed)
│   ├── services.py        # send_otp_email() — single OTP lifecycle service
│   ├── serializers.py     # One serializer per endpoint
│   ├── views.py           # Thin views — logic in services/serializers
│   └── urls.py
└── profiles/              # Investor & Sponsor onboarding and verification
    ├── models.py          # InvestorProfile, SponsorProfile, Industry, Document
    ├── serializers.py     # UserFieldsMixin (DRY), role/profile serializers
    ├── views.py           # Permission-class-driven, no manual role checks
    ├── admin.py
    └── urls.py
```

---

## Quick Start

```bash
# 1. Create and activate virtual environment
python3 -m venv .venv && source .venv/bin/activate

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env with your values

# 4. Run migrations
python manage.py migrate

# 5. Create a superuser
python manage.py createsuperuser

# 6. Start development server
python manage.py runserver
```

---

## API Reference

All endpoints are prefixed with `/api/v1/`.

### Authentication (`/api/v1/auth/`)

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `register/` | Public | Create account, sends OTP email |
| `POST` | `login/` | Public | Login with email+password, returns JWT |
| `POST` | `logout/` | JWT | Blacklist refresh token |
| `POST` | `token/refresh/` | Public | Refresh access token |
| `POST` | `verify-otp/` | Public | Verify email OTP → returns JWT pair |
| `POST` | `resend-otp/` | Public | Resend registration OTP |
| `POST` | `forgot-password/` | Public | Send password reset OTP |
| `POST` | `reset-password/` | Public | Set new password using OTP |

### Profiles (`/api/v1/profiles/`)

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `set-role/` | JWT + verified | Choose INVESTOR or SPONSOR role |
| `GET` | `industries/` | JWT | List all available industries |
| `GET/PATCH` | `investor/onboarding/` | JWT + Investor | View/update investor profile |
| `GET/PATCH` | `sponsor/onboarding/` | JWT + Sponsor | View/update sponsor profile |
| `POST` | `documents/upload/` | JWT + verified | Upload PDF/JPG/PNG (max 5 MB) |
| `GET` | `verification-status/` | JWT + verified | Check compliance review status |

---

## Key Design Decisions

- **Single `.env` file** — all secrets and environment config live here, never in code.
- **`core` app** — shared utilities (`TimeStampedModel`, response helpers, permissions, throttles) available to every app with no circular imports.
- **Cryptographic OTP** — uses Python's `secrets` module, not `random`.
- **DB indexes** — on `email`, `role`, OTP lookup fields, and verification status.
- **Service layer** — `authentication/services.py` owns the full OTP lifecycle. Views only call it.
- **DRY serializers** — `UserFieldsMixin` eliminates duplicated `update()` logic between Investor and Sponsor serializers.
- **Permission classes** — `IsEmailVerified`, `IsInvestor`, `IsSponsor` in `core/permissions.py` replace manual role-check if-blocks in every view.
- **`save(update_fields=[...])`** — used on all model saves to avoid full-row writes.
- **Rate limiting** — `AuthRateThrottle` (5/min) on every auth endpoint; standard anon/user throttles globally.
- **API versioning** — all routes live under `/api/v1/` — a v2 is one `include()` line away.
- **Token blacklisting** — `ROTATE_REFRESH_TOKENS + BLACKLIST_AFTER_ROTATION` ensures logout is real.
