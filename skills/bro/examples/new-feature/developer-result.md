# Developer Result — new-feature

## Changed Files
- `services/oauth.py` — new: `OAuthService` with `exchange_code()` and `refresh_access_token()`
- `routes/auth.py` — added `POST /auth/oauth/{provider}` handler
- `config/oauth.py` — new: `OAuthConfig` dataclass, loads from env
- `models/token.py` — added `refresh_token_encrypted` field
- `tests/test_oauth.py` — 14 tests covering happy path, invalid code, expired code, bad provider

## Key Decisions
- Used `httpx` for async HTTP calls to Google/GitHub token endpoints (consistent with existing `services/`).
- Refresh token encryption uses `cryptography.fernet` (already in project dependencies).
- JWT signing key loaded from `JWT_PRIVATE_KEY` env var; public key exposed via `/.well-known/jwks.json`.
- All new code is behind feature flag `ENABLE_OAUTH` (defaults to `True`).
