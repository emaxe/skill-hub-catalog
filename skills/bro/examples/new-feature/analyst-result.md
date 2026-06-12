# Analyst Result — new-feature

## Spec: OAuth 2.0 Authentication Endpoint

### Requirements
1. **Endpoint**: `POST /auth/oauth/{provider}` (provider ∈ {google, github})
2. **Flow**: Authorization code → exchange for access token → store refresh token → return JWT
3. **Security**: Refresh tokens encrypted at rest (AES-256-GCM). JWT signed with RS256.
4. **Config**: Client IDs, secrets, and redirect URIs from environment variables (never commit secrets).
5. **Error handling**: Standard HTTP 400/401/500 with JSON error bodies.

### Affected Files / Modules
- `routes/auth.py` — add new endpoint
- `services/oauth.py` — new service for provider-specific token exchange
- `config/oauth.py` — new config loader for OAuth credentials
- `models/token.py` — extend to store refresh tokens
- `tests/test_oauth.py` — new test suite

### Constraints
- Must follow existing `auth/` module patterns (dependency injection, async handlers).
- Must not break existing `/auth/login` and `/auth/register` endpoints.
