# Authentication Notes

Authentication starts with email/password registration and OAuth2 password-form login.

Current behavior:

- `POST /api/v1/users` creates users from JSON.
- `POST /api/v1/auth/token` accepts OAuth2 password form fields, using `username` for email.
- Access tokens are bearer tokens signed with the configured `AUTH_SECRET_KEY`.
- Refresh tokens are opaque, stored as hashes, expire after 30 days by default, and rotate on use.
- `POST /api/v1/auth/refresh` returns a new access token and refresh token.
- `POST /api/v1/auth/logout` revokes the submitted refresh token for the current client session.
- Password reset tokens are opaque, stored as hashes, expire after 30 minutes by default, and revoke existing refresh tokens when used.
- Password reset delivery uses configurable SMTP and the iOS client accepts the emailed one-time token.
- Refresh-token rotation uses row locking and token families; replaying a rotated token revokes the family.
- Authentication endpoints use a bounded per-process sliding-window rate limiter.
- `POST /api/v1/auth/password-reset/request` returns a generic message for registered and unregistered emails.
- `POST /api/v1/auth/password-reset/confirm` consumes a reset token and sets the new password.
- Passwords are stored with PBKDF2-HMAC-SHA256 and per-password salts.
- Users can update their email, password, and profile, but not their own `is_active` flag.

Next decisions:

- Account verification flow.
- Admin-only account management endpoints.
- Device/session listing if users need to revoke another active device.
- TODO: add cleanup jobs for expired refresh, reset, and verification tokens.
