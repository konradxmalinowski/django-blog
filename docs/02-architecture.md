# Architektura

## Stack technologiczny

| Warstwa | Technologia |
|---------|-------------|
| Backend | Python 3.14, Django 5.2 |
| Baza danych | SQLite (dev), PostgreSQL-ready |
| ORM | Django ORM |
| REST API | Django REST Framework 3.17 |
| Markdown | django-markdownx + bleach |
| Tagi | django-taggit |
| 2FA | pyotp (TOTP) + qrcode |
| Brute-force | django-axes |
| Rate limiting | django-ratelimit |
| Sanityzacja | bleach |
| Obrazy | Pillow |
| Env vars | python-decouple |
| Frontend | Vanilla JS, własny terminal CSS |
| Font | JetBrains Mono (Google Fonts) |
| Testy | pytest-django, pytest-cov |

---

## Modele danych

### `blog.Post`

| Pole | Typ | Opis |
|------|-----|------|
| `title` | CharField(250) | Tytuł posta |
| `slug` | SlugField(unique_for_date='publish') | URL slug |
| `author` | FK(User) | Autor |
| `category` | FK(Category, null=True) | Kategoria |
| `body` | MarkdownxField | Treść (Markdown) |
| `excerpt` | TextField(500) | Krótki opis |
| `cover_image` | ImageField | Zdjęcie nagłówkowe |
| `tags` | TaggableManager | Tagi (taggit) |
| `publish` | DateTimeField | Data publikacji |
| `status` | CharField | `draft` / `published` |
| `reading_time` | PositiveIntegerField | Czas czytania (min) |
| `views_count` | PositiveIntegerField | Liczba wyświetleń |
| `meta_description` | CharField(160) | SEO meta description |

Managery: `Post.objects` (wszystkie), `Post.published` (tylko `status='published'`).

### `blog.Category`

| Pole | Typ |
|------|-----|
| `name` | CharField(100) |
| `slug` | SlugField(unique) |
| `description` | TextField |
| `color` | CharField(7) - hex kolor |
| `meta_description` | CharField(160) |

### `blog.Comment`

| Pole | Typ |
|------|-----|
| `post` | FK(Post) |
| `user` | FK(User, null=True) - opcjonalny |
| `name` | CharField(80) |
| `email` | EmailField |
| `body` | TextField - bleach-sanitized |
| `active` | BooleanField(False) - moderacja |
| `created` | DateTimeField(auto_now_add) |

### `blog.PostReaction`

Unikalna para `(post, user)` - "lajk" posta.

### `blog.Bookmark`

Unikalna para `(user, post)` - zapisany post.

### `blog.Subscriber`

| Pole | Typ |
|------|-----|
| `email` | EmailField(unique) |
| `confirmed` | BooleanField(False) |
| `token` | UUIDField - link potwierdzający |
| `created_at` | DateTimeField |

### `accounts.UserProfile`

OneToOne z User. Pola: `bio`, `avatar`, `github_url`, `website`, `totp_secret`, `two_factor_enabled`, `notify_comments`.

### `accounts.EmailVerificationToken`

OneToOne z User. UUID token, TTL 24h, pole `used`.

### `accounts.TwoFactorBackupCode`

FK(User). `code_hash` (PBKDF2), `used`, `created_at`. 8 kodów na użytkownika, jednorazowe.

### `accounts.AuditLog`

FK(User). Akcje: `login`, `logout`, `password_change`, `email_change`, `2fa_enabled`, `2fa_disabled`, `2fa_failed`, `backup_code_used`, `register`. IP + User-Agent.

---

## URL namespaces

### `blog:`

| Name | URL | Opis |
|------|-----|------|
| `post_list` | `/` | Lista postów |
| `post_detail` | `/<rok>/<mies>/<dzień>/<slug>/` | Szczegół posta |
| `post_search` | `/search/` | Wyszukiwarka |
| `post_list_by_tag` | `/tag/<slug>/` | Posty po tagu |
| `post_list_by_category` | `/category/<slug>/` | Posty po kategorii |
| `post_list_by_author` | `/author/<username>/` | Posty autora |
| `post_share` | `/<id>/share/` | Udostępnij emailem |
| `toggle_reaction` | `/posts/<id>/react/` | Lajk (AJAX) |
| `toggle_bookmark` | `/posts/<id>/bookmark/` | Zakładka (AJAX) |
| `bookmark_list` | `/bookmarks/` | Lista zakładek |
| `author_post_list` | `/author/posts/` | Panel autora/moderatora |
| `author_post_new` | `/author/posts/new/` | Nowy post |
| `author_post_edit` | `/author/posts/<slug>/edit/` | Edytuj post |
| `author_post_delete` | `/author/posts/<slug>/delete/` | Usuń post |
| `newsletter_subscribe` | `/newsletter/subscribe/` | Subskrypcja |
| `newsletter_confirm` | `/newsletter/confirm/<uuid>/` | Potwierdzenie |
| `newsletter_unsubscribe` | `/newsletter/unsubscribe/<uuid>/` | Wypisanie |
| `post_feed` | `/feed/` | RSS global |
| `category_feed` | `/feed/category/<slug>/` | RSS per-category |

### `accounts:`

| Name | URL |
|------|-----|
| `register` | `/accounts/register/` |
| `login` | `/accounts/login/` |
| `logout` | `/accounts/logout/` |
| `profile` | `/accounts/profile/` |
| `settings` | `/accounts/settings/` |
| `change_password` | `/accounts/settings/password/` |
| `change_email` | `/accounts/settings/email/` |
| `setup_2fa` | `/accounts/settings/2fa/` |
| `disable_2fa` | `/accounts/settings/2fa/disable/` |
| `verify_2fa` | `/accounts/2fa/verify/` |
| `show_backup_codes` | `/accounts/settings/2fa/backup-codes/` |
| `regenerate_backup_codes` | `/accounts/settings/2fa/backup-codes/regenerate/` |
| `verify_email_sent` | `/accounts/verify-email/sent/` |
| `verify_email` | `/accounts/verify-email/<uuid>/` |
| `password_reset` | `/accounts/password-reset/` |
| `public_profile` | `/accounts/<username>/` |

### `api:`

| Endpoint | Metody | Auth |
|----------|--------|------|
| `/api/posts/` | GET, POST | Token (POST) |
| `/api/posts/<slug>/` | GET, PUT, PATCH, DELETE | Token (zapis) |
| `/api/posts/<slug>/comments/` | GET, POST | - |
| `/api/tags/` | GET | - |
| `/api/categories/` | GET | - |
| `/api/auth/token/` | POST | - |

---

## Przepływ rejestracji i aktywacji

```
POST /accounts/register/
  → user.is_active = False
  → EmailVerificationToken (UUID, 24h)
  → email z linkiem → /accounts/verify-email/<uuid>/
  → użytkownik klika → is_active = True, login
```

## Przepływ 2FA

```
POST /accounts/settings/2fa/
  → generuje totp_secret (pyotp.random_base32)
  → wyświetla QR code (base64 PNG)
  → użytkownik wpisuje kod z aplikacji
  → two_factor_enabled = True
  → generuje 8 backup codes (PBKDF2)
  → wyświetla backup codes jednorazowo

Login z 2FA:
  POST /accounts/login/
  → django-axes sprawdza lockout
  → authenticate()
  → session['2fa_verified'] = False
  → redirect → /accounts/2fa/verify/?next=<url>
  → TwoFactorMiddleware blokuje dostęp aż do weryfikacji
  → POST /accounts/2fa/verify/ (TOTP lub backup code)
  → session['2fa_verified'] = True
  → redirect next (walidowany przez url_has_allowed_host_and_scheme)
```

---

## Middleware stack (kolejność)

1. `SecurityMiddleware`
2. `AxesMiddleware`
3. `SessionMiddleware`
4. `CommonMiddleware`
5. `CsrfViewMiddleware`
6. `AuthenticationMiddleware`
7. `MessageMiddleware`
8. `XFrameOptionsMiddleware`
9. `SecurityHeadersMiddleware` (własny - CSP, Permissions-Policy)
10. `TwoFactorMiddleware` (własny - wymusza weryfikację 2FA)
