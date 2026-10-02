# Security notes

Honest mapping against the OWASP Top 10 — what RootCause actually does,
not a checklist pretending everything's solved.

| Risk | Status | Where |
|---|---|---|
| A01 Broken Access Control | Partial | Authenticated requests use the JWT's identity, never the client-supplied `user_id` (`_resolve_user_id` in `main.py`) — tested in `test_api.py::test_logged_in_user_cannot_spoof_a_different_user_id`. No admin roles exist yet. |
| A02 Cryptographic Failures | Done | Passwords: PBKDF2-SHA256, 260k iterations, stdlib only (`auth.py`). JWTs signed HS256. **Set `JWT_SECRET` before deploying** — the default is an obvious dev placeholder on purpose. |
| A03 Injection | Done | SQLAlchemy ORM everywhere — no raw/string-formatted SQL anywhere in the codebase. |
| A04 Insecure Design | Partial | Rate limiting on auth + mutating endpoints (`security.py`). No CAPTCHA, no account lockout after N failed logins — add before this has real users. |
| A05 Security Misconfiguration | Partial | Security headers via middleware (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`). CORS from `ALLOWED_ORIGINS` env, not hardcoded — but defaults to `*` if you forget to set it. **Set `ALLOWED_ORIGINS` in production.** |
| A06 Vulnerable Components | Not automated | No Dependabot/`pip-audit` wired in yet — `requirements.txt` versions are lower-bounded (`>=`), not pinned exactly, which cuts both ways (gets patches automatically, but isn't reproducible). Worth pinning + scanning before production. |
| A07 Auth Failures | Partial | Password hashing + JWT expiry (7 days default) done. No MFA, no email verification on register, no account lockout. Forgot-password exists but has no real email provider wired in — see `README.md`. |
| A08 Data Integrity Failures | N/A for now | No deserialization of untrusted blobs, no auto-update mechanism. |
| A09 Logging & Monitoring | Not done | No centralized logging/alerting. `uvicorn`'s own access logs are all you get today. |
| A10 SSRF | N/A | No server-side fetch of user-supplied URLs. |

## Rate limiting

`security.py`'s `RateLimitMiddleware` is a sliding-window limiter, in
memory, per process — 20 requests/60s by default on `/api/auth/*`,
`/api/diagnose*`, `/api/bughunt/guess`, `/api/teachback`. This is
correctly tested (`test_rate_limit_eventually_kicks_in_on_auth`) but
**won't be shared across replicas** if you scale the backend
horizontally — swap it for a Redis-backed limiter first.

## Before this touches real user data

1. Set `JWT_SECRET` and `ALLOWED_ORIGINS` (both default to obviously-unsafe
   dev values on purpose, so you notice).
2. Wire a real email provider into `forgot_password()` in `main.py` and
   stop returning `dev_reset_token` in the response.
3. Pin `requirements.txt` exactly and add `pip-audit` (or Dependabot) to CI.
4. Add structured logging + an error tracker (Sentry or similar).
5. Add account lockout / CAPTCHA after repeated failed logins.
