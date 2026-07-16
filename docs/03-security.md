# Bezpieczeństwo

## Przegląd warstw

| Warstwa | Mechanizm |
|---------|-----------|
| Brute-force | django-axes: 5 prób → lockout 1h |
| Rate limiting | django-ratelimit: IP-based na register, login, 2FA, newsletter |
| XSS (komentarze) | bleach: whitelist tagów HTML |
| XSS (Markdown) | bleach na output markdownify |
| XSS (ToC) | `escape()` przed `mark_safe` w render_toc |
| CSRF | Django CsrfViewMiddleware na wszystkich POST |
| Open redirect | `url_has_allowed_host_and_scheme` w verify_2fa |
| SQL injection | Django ORM (parametrized queries) |
| Clickjacking | X-Frame-Options: DENY |
| MIME sniffing | X-Content-Type-Options: nosniff |
| Referrer | Referrer-Policy: strict-origin-when-cross-origin |
| CSP | własny middleware - script-src 'self' 'unsafe-inline' |
| Hasła | Django PBKDF2 (domyślny hasher) |
| Backup codes | PBKDF2 (make_password/check_password) |
| Session | HTTPONLY, SAMESITE=Lax, 14-dniowy TTL |
| HTTPS (prod) | SESSION_COOKIE_SECURE, CSRF_COOKIE_SECURE, HSTS 1y |
| Audit log | AuditLog model - wszystkie zdarzenia security |
| Profanity | Filtr przekleństw (PL+EN) w CommentForm |

---

## django-axes - brute-force

Konfiguracja w `settings/base.py`:

```python
AXES_FAILURE_LIMIT = 5       # maksymalna liczba prób
AXES_COOLOFF_TIME = 1        # czas blokady w godzinach
AXES_RESET_ON_SUCCESS = True # reset licznika po sukcesie
AXES_LOCKOUT_TEMPLATE = 'accounts/locked_out.html'
```

Po 5 nieudanych próbach → HTTP 403 z szablonen `locked_out.html`.

---

## Rate limiting

| Endpoint | Limit | Klucz |
|----------|-------|-------|
| `register` | 10/h | IP |
| `post_detail` (POST) | 5/min | IP |
| `verify_2fa` (POST) | 5/min | user_or_ip |
| `newsletter_subscribe` | 5/h | IP |

Przekroczenie limitu → HTTP 429 (obsługiwany przez `handler429`).

---

## Weryfikacja emaila

1. Rejestracja tworzy użytkownika z `is_active=False`
2. Generuje `EmailVerificationToken` (UUID, ważny 24h)
3. Wysyła email z linkiem `/accounts/verify-email/<uuid>/`
4. Kliknięcie → `is_active=True`, automatyczne zalogowanie

---

## 2FA TOTP

- Secret generowany przez `pyotp.random_base32()` (128-bit entropy)
- QR code generowany jako base64 PNG (qrcode + Pillow)
- Kompatybilny z: Google Authenticator, Authy, Bitwarden, 1Password
- Po włączeniu 2FA: TwoFactorMiddleware wymusza weryfikację przy każdej sesji

### Backup codes

- 8 jednorazowych kodów (10-znakowe hex uppercase)
- Hashowane PBKDF2 przez `django.contrib.auth.hashers.make_password`
- Weryfikacja iteracyjna (O(8)) - `check_password` per rekord
- Zużyty kod oznaczany `used=True`, nie może być użyty ponownie
- Regeneracja wymaga aktualnego kodu TOTP

---

## XSS sanityzacja

### Komentarze (CommentForm)

Whitelist tagów:
```python
ALLOWED_COMMENT_TAGS = ['b', 'i', 'em', 'strong', 'code', 'pre', 'a', 'p', 'br']
ALLOWED_COMMENT_ATTRS = {'a': ['href', 'title']}
```

Walidacja:
1. `bleach.clean()` - usuwa niedozwolone tagi
2. `contains_profanity()` - odrzuca formularz jeśli wykryte przekleństwa

### Markdown (blog_tags.py / markdownify)

Pełna lista dozwolonych tagów w `ALLOWED_TAGS` (markdownify filter).

### Table of Contents

Tekst nagłówka escapowany przez `django.utils.html.escape()` przed wstrzyknięciem do `mark_safe`.

---

## Audit log

Każde zdarzenie security zapisywane do `AuditLog`:

| Akcja | Kiedy |
|-------|-------|
| `login` | Udane zalogowanie |
| `logout` | Wylogowanie |
| `register` | Rejestracja |
| `password_change` | Zmiana hasła |
| `email_change` | Zmiana emaila |
| `2fa_enabled` | Włączenie 2FA |
| `2fa_disabled` | Wyłączenie 2FA |
| `2fa_failed` | Nieprawidłowy kod 2FA |
| `backup_code_used` | Użycie kodu zapasowego |

Każdy wpis zawiera IP (z X-Forwarded-For lub REMOTE_ADDR) i User-Agent.

---

## Ustawienia produkcyjne

Plik `devlog/settings/production.py`:

```python
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000      # 1 rok
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
```

Użycie: `DJANGO_SETTINGS_MODULE=devlog.settings.production`

---

## Filtr przekleństw

Plik `apps/blog/profanity.py`.  
Lista obejmuje popularne polskie i angielskie przekleństwa.  
Walidacja w `CommentForm` - pola `name` i `body`.  
Odrzucenie formularza z komunikatem: *"Komentarz zawiera niedozwolone słowa."*

Funkcje pomocnicze:
- `contains_profanity(text: str) -> bool`
- `censor(text: str, char='*') -> str` - do użycia w admin/moderation

---

## Logi bezpieczeństwa

`logs/security.log` - wszystkie zdarzenia `django.security` (INFO+):
- nieudane logowania (axes)
- CSRF failures
- błędy SSL/TLS

`logs/django.log` - błędy aplikacji (WARNING+).
