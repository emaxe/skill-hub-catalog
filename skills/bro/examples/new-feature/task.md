# Task: Add OAuth 2.0 authentication endpoint

**User request:**
> We need a new `/auth/oauth` endpoint that supports Google and GitHub OAuth 2.0 flows. It should exchange authorization codes for access tokens, store refresh tokens securely, and return a JWT to the client. Use existing `auth/` module patterns.

**Scope:** Medium feature — new API endpoint, new service module, updates to config and tests.
