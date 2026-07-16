# Security Features - DevLog

## Task Description

Implement 5 security features for the DevLog Django blog:
1. `notify_comments` field in UserProfile
2. Email verification on registration
3. Password reset flow
4. 2FA backup codes
5. Audit log

## Acceptance Criteria

- All models migrate cleanly, `manage.py check` returns 0 issues
- Email verification blocks login until email confirmed
- Password reset flow works end-to-end (console email backend in dev)
- Backup codes generated on 2FA setup, hashed in DB, consumable once
- Audit log captures all listed actions with IP and user-agent

## Files to Modify

- `apps/accounts/models.py` - add EmailVerificationToken, TwoFactorBackupCode, AuditLog, notify_comments
- `apps/accounts/forms.py` - add notify_comments to UserProfileForm
- `apps/accounts/views.py` - register, setup_2fa, disable_2fa, verify_2fa; add new views
- `apps/accounts/urls.py` - add new URL patterns before `<str:username>/`
- `apps/accounts/utils.py` - new file with log_action, get_client_ip

## Files to Create

- `apps/accounts/utils.py`
- `templates/accounts/verify_email_sent.html`
- `templates/accounts/backup_codes.html`
- `templates/accounts/password_reset.html`
- `templates/accounts/password_reset_done.html`
- `templates/accounts/password_reset_confirm.html`
- `templates/accounts/password_reset_complete.html`
- `templates/email/verify_email_subject.txt`
- `templates/email/verify_email.txt`
- `templates/registration/password_reset_email.txt`
- `templates/registration/password_reset_subject.txt`

## DB Changes

- New field: `UserProfile.notify_comments` (BooleanField, default=True)
- New model: `EmailVerificationToken`
- New model: `TwoFactorBackupCode`
- New model: `AuditLog`

## Error Handling Strategy

- Invalid/used verification tokens: messages.error + redirect to login
- Backup codes stored as SHA-256 hashes, never plaintext after generation
- AuditLog creation wrapped in try/except to never break primary flow
- log_action silently fails on exception
