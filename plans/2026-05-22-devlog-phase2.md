# DevLog - Plan Fazy 2

Data: 2026-05-22  
Autor: Konrad

---

## Przegląd

Faza 2 rozszerza blog o pełen zestaw funkcjonalności produkcyjnej aplikacji:
bezpieczeństwo (rate limiting, blokada konta, weryfikacja e-mail, backup codes 2FA),
interakcje użytkownika (reakcje, zakładki, newsletter, panel autora),
SEO/jakość (ToC, sitemap priorytety, Core Web Vitals)
oraz pokrycie testami.

Wszystkie etapy są niezależne - można je wdrażać w dowolnej kolejności,
ale zalecana sekwencja minimalizuje konflikty (np. weryfikacja e-mail musi być
przed blokadą konta, bo zmienia pole `is_active`).

---

## Etap 1 - Bezpieczeństwo (krytyczne)

### 1.1 Sanityzacja komentarzy
**Ryzyko: XSS.** Sprawdzić i naprawić natychmiast.

- [ ] `grep -r "bleach" apps/blog/` - czy `Comment.body` przechodzi przez `bleach.clean()` przed zapisem
- [ ] Jeśli nie: dodać `clean()` w `Comment.save()` lub w formularzu
- [ ] Dozwolone tagi: `['b', 'i', 'em', 'strong', 'a', 'code']`, atrybuty: `{'a': ['href']}`
- [ ] Test: spróbuj zapisać komentarz z `<script>alert(1)</script>` - musi być escaped

**Pliki:** `apps/blog/models.py`, `apps/blog/forms.py`

---

### 1.2 Weryfikacja e-maila przy rejestracji

Zmiana: nowe konta mają `is_active=False` do czasu kliknięcia w link.

- [ ] W `RegisterForm.save()`: `user.is_active = False`, potem `user.save()`
- [ ] Nowy model `EmailVerificationToken`: `user` (FK), `token` (uuid4), `created_at`, `used`
- [ ] Nowa migracja: `makemigrations accounts`
- [ ] W widoku `register`: po zapisaniu usera → wygeneruj token → wyślij e-mail
- [ ] Nowy URL: `accounts/verify-email/<token>/` → widok `verify_email`
- [ ] Widok `verify_email`: weryfikuje token (max 24h), ustawia `is_active=True`, `token.used=True`, loguje usera, redirect do profilu
- [ ] Szablon e-maila: `templates/email/verify_email.html` + `.txt`
- [ ] Szablon strony: `templates/accounts/verify_email_sent.html` (info "sprawdź skrzynkę")
- [ ] Uwaga: zablokować login dla `is_active=False` - Django robi to automatycznie w `LoginView`

**Pliki:** `apps/accounts/models.py`, `apps/accounts/views.py`, `apps/accounts/urls.py`, `templates/accounts/`, `templates/email/`  
**Wymaga:** działającego backendu e-mail (lokalnie: console backend)

---

### 1.3 Rate limiting na login / rejestrację / komentarze

Pakiet: `django-ratelimit`

- [ ] `pip install django-ratelimit`
- [ ] Dodać do `requirements.txt`
- [ ] Dekorator `@ratelimit(key='ip', rate='5/m', block=True)` na widoku `register`
- [ ] Dekorator na `LoginView` - wymaga FBV wrappera lub custom `LoginView`
- [ ] Dekorator na `post_detail` (metoda POST - dodawanie komentarza): `rate='3/m'`
- [ ] Obsługa błędu 429: szablon `templates/429.html` z info "za dużo prób, spróbuj za chwilę"
- [ ] Dodać `handler429` w `devlog/urls.py`

**Pliki:** `apps/accounts/views.py`, `apps/blog/views.py`, `devlog/urls.py`, `templates/429.html`

---

### 1.4 Blokada konta po nieudanych loginach

Pakiet: `django-axes`

- [ ] `pip install django-axes`
- [ ] Dodać `'axes'` do `INSTALLED_APPS`
- [ ] Dodać `'axes.middleware.AxesMiddleware'` do `MIDDLEWARE` (przed `SessionMiddleware`)
- [ ] Dodać `'axes.backends.AxesStandaloneBackend'` do `AUTHENTICATION_BACKENDS`
- [ ] Konfiguracja w `base.py`:
  ```python
  AXES_FAILURE_LIMIT = 5          # blokada po 5 próbach
  AXES_COOLOFF_TIME = 1           # odblokowanie po 1h
  AXES_LOCKOUT_TEMPLATE = 'accounts/locked_out.html'
  AXES_RESET_ON_SUCCESS = True
  ```
- [ ] Nowa migracja: `makemigrations` (axes ma własne tabele)
- [ ] Szablon: `templates/accounts/locked_out.html`

**Pliki:** `devlog/settings/base.py`, `templates/accounts/locked_out.html`

---

### 1.5 Backup codes dla 2FA

Gdy użytkownik włącza 2FA, generowane jest 8 jednorazowych kodów zapasowych.

- [ ] Nowy model `TwoFactorBackupCode`: `user` (FK), `code` (CharField 10 znaków, hashed), `used` (bool)
- [ ] W widoku `setup_2fa`: po potwierdzeniu TOTP → wygeneruj 8 kodów → zapisz zahashowane → wyświetl raz (nie da się odtworzyć)
- [ ] Nowy szablon: `templates/accounts/backup_codes.html` - lista kodów z przyciskiem "Pobierz jako TXT"
- [ ] Modyfikacja widoku `verify_2fa`: jeśli TOTP nieprawidłowy, sprawdź backup codes (constant-time compare)
- [ ] Nowy widok `regenerate_backup_codes` - invaliduje stare, generuje nowe (wymaga TOTP)
- [ ] Dodać link "Kody zapasowe" w ustawieniach konta

**Pliki:** `apps/accounts/models.py`, `apps/accounts/views.py`, `apps/accounts/urls.py`, `templates/accounts/`

---

### 1.6 Session timeout

- [ ] W `devlog/settings/base.py`:
  ```python
  SESSION_COOKIE_AGE = 60 * 60 * 24 * 14   # 14 dni
  SESSION_EXPIRE_AT_BROWSER_CLOSE = False    # lub True dla większego bezpieczeństwa
  SESSION_SAVE_EVERY_REQUEST = True          # odświeżanie przy każdym request
  ```
- [ ] Opcjonalnie: middleware wylogowujący po X minutach bezczynności (sprawdza `session['last_activity']`)

**Pliki:** `devlog/settings/base.py`

---

### 1.7 Audit log

Rejestrowanie ważnych akcji bezpieczeństwa.

- [ ] Nowy model `AuditLog`: `user` (FK), `action` (CharField), `ip` (GenericIPAddressField), `user_agent` (TextField), `created_at`
- [ ] Akcje do logowania: login, logout, zmiana hasła, zmiana e-mail, włączenie/wyłączenie 2FA, nieudany login 2FA
- [ ] Helper `log_action(request, action)` w `apps/accounts/utils.py`
- [ ] Widok podglądu logów dla admina (tylko `is_staff`)

**Pliki:** `apps/accounts/models.py`, `apps/accounts/utils.py`, `apps/accounts/views.py`

---

## Etap 2 - Funkcjonalności użytkownika

### 2.1 Reset hasła

Wbudowany w Django - tylko URL-e i szablony.

- [ ] Dodać do `apps/accounts/urls.py`:
  ```python
  path('password-reset/', auth_views.PasswordResetView.as_view(...), name='password_reset'),
  path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(...), name='password_reset_done'),
  path('password-reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(...), name='password_reset_confirm'),
  path('password-reset/complete/', auth_views.PasswordResetCompleteView.as_view(...), name='password_reset_complete'),
  ```
- [ ] Szablony: `password_reset.html`, `password_reset_done.html`, `password_reset_confirm.html`, `password_reset_complete.html`
- [ ] Szablon e-maila: `templates/registration/password_reset_email.html`
- [ ] Dodać link "Zapomniałem hasła" na stronie logowania

**Pliki:** `apps/accounts/urls.py`, `templates/accounts/`, `templates/registration/`

---

### 2.2 Powiadomienie autora o komentarzu

- [ ] W widoku `post_detail` (po zapisaniu komentarza): wyślij e-mail do `post.author.email`
- [ ] Szablon e-maila: `templates/email/new_comment.html` + `.txt`
- [ ] Warunek: wyślij tylko jeśli komentarz aktywny (lub zawsze, a admin moderuje)
- [ ] Opcja "wyłącz powiadomienia" w ustawieniach profilu (`UserProfile.notify_comments = BooleanField`)

**Pliki:** `apps/blog/views.py`, `apps/accounts/models.py`, `templates/email/`

---

### 2.3 Reakcje na posty (likes)

- [ ] Nowy model `PostReaction`: `post` (FK), `user` (FK), `created_at` - unique_together `(post, user)`
- [ ] Nowa migracja
- [ ] Nowy widok `toggle_reaction(request, post_id)` - POST only, zwraca JSON `{count, liked}`
- [ ] Dodać URL: `blog/posts/<id>/react/`
- [ ] W `post_detail.html`: przycisk ♥ z licznikiem, obsługa JS (fetch POST, aktualizacja UI bez reload)
- [ ] Licznik wyświetleń: dodać `Post.views_count = PositiveIntegerField(default=0)`, inkrementować w `post_detail` (tylko dla niezalogowanych lub raz na sesję)
- [ ] Wyświetlić views_count w meta posta

**Pliki:** `apps/blog/models.py`, `apps/blog/views.py`, `apps/blog/urls.py`, `templates/blog/post_detail.html`, `static/js/terminal.js`

---

### 2.4 Zakładki / zapisane posty

- [ ] Nowy model `Bookmark`: `user` (FK), `post` (FK), `created_at` - unique_together `(user, post)`
- [ ] Nowy widok `toggle_bookmark(request, post_id)` - POST, zwraca JSON
- [ ] Widok `bookmark_list` - lista zapisanych postów zalogowanego użytkownika
- [ ] Dodać URL: `accounts/bookmarks/`
- [ ] Przycisk zakładki w `post_detail.html` (obok reakcji)
- [ ] Link "Moje zakładki" na stronie profilu

**Pliki:** `apps/blog/models.py`, `apps/blog/views.py`, `apps/blog/urls.py`, `templates/`, `templates/accounts/profile.html`

---

### 2.5 Newsletter

- [ ] Nowy model `Subscriber`: `email` (unique), `confirmed` (bool), `token` (uuid4), `created_at`
- [ ] Widok `newsletter_subscribe` - formularz z e-mailem, wysyła e-mail potwierdzający
- [ ] Widok `newsletter_confirm/<token>/` - potwierdza subskrypcję
- [ ] Widok `newsletter_unsubscribe/<token>/` - wypisuje
- [ ] Signal lub override `Post.save()`: gdy `status` zmienia się na `'published'` → wyślij e-mail do wszystkich `confirmed` subskrybentów
- [ ] Widget zapisu w sidebarze (`templates/partials/sidebar.html`)
- [ ] Szablon e-maila: `templates/email/newsletter.html` + `.txt`

**Pliki:** nowa app `apps/newsletter/` lub model w `apps/blog/`, `templates/partials/sidebar.html`

---

### 2.6 Panel autora (CRUD postów)

- [ ] Nowe URL-e w `apps/blog/urls.py`:
  - `GET /author/posts/` - lista własnych postów (szkice + opublikowane)
  - `GET/POST /author/posts/new/` - nowy post
  - `GET/POST /author/posts/<slug>/edit/` - edycja
  - `POST /author/posts/<slug>/delete/` - usunięcie (confirm dialog)
- [ ] `PostForm(ModelForm)` - pola: title, excerpt, body, category, tags, cover_image, status
- [ ] Markdown editor: `easymde` (CDN) lub `SimpleMDE` - lekki JS editor z podglądem na żywo
- [ ] Warunek dostępu: `post.author == request.user` (lub `is_staff`)
- [ ] Szablony: `author_post_list.html`, `author_post_form.html`, `author_post_confirm_delete.html`
- [ ] Link "Moje posty" w nawigacji gdy zalogowany

**Pliki:** `apps/blog/views.py`, `apps/blog/forms.py`, `apps/blog/urls.py`, `templates/blog/`, `base.html`

---

### 2.7 Paginacja komentarzy

- [ ] W widoku `post_detail`: paginacja komentarzy - 10 na stronę, `?comment_page=N`
- [ ] Oddzielny `Paginator` dla komentarzy (nie mylić z paginacją postów)
- [ ] W szablonie: blok paginacji pod listą komentarzy

**Pliki:** `apps/blog/views.py`, `templates/blog/post_detail.html`

---

### 2.8 Czas ostatniej aktywności

- [ ] W `templates/accounts/public_profile.html`: dodać `{{ profile_user.last_login|date:"Y-m-d" }}`
- [ ] Wyświetlić jako: `ostatnia aktywność: 2026-05-20`
- [ ] Jeśli `last_login` jest None: ukryć sekcję

**Pliki:** `templates/accounts/public_profile.html`

---

## Etap 3 - UX i treść

### 3.1 Spis treści (ToC)

- [ ] Napisać `extract_toc(markdown_text)` w `apps/blog/templatetags/blog_tags.py`:
  - Regex nagłówków `## Tytuł` → `{level, text, anchor}`
  - Generuj HTML listy z `href="#anchor"`
- [ ] Nowy template tag: `{% toc post.body %}`
- [ ] Wyświetlać ToC w sidebarze przy `post_detail` jeśli post ma >3 nagłówki
- [ ] JS: podświetlanie aktywnej sekcji przy scrollowaniu (`IntersectionObserver`)

**Pliki:** `apps/blog/templatetags/blog_tags.py`, `templates/blog/post_detail.html`, `static/js/terminal.js`

---

### 3.2 Dark/Light mode toggle

- [ ] Dodać CSS custom properties dla light mode w `terminal.css` (klasa `.light-mode` na `body`)
- [ ] Przycisk w navbarze: `☀️` / `🌙` (lub `[light]` / `[dark]` w stylu terminal)
- [ ] JS: toggle klasy + zapis w `localStorage`, init z `prefers-color-scheme`
- [ ] Upewnić się że wszystkie kolory to CSS variables (już tak jest)

**Pliki:** `static/css/terminal.css`, `static/js/terminal.js`, `templates/base.html`

---

## Etap 4 - SEO

### 4.1 Sitemap z priorytetami

- [ ] W `apps/blog/sitemaps.py`: nadpisać `priority` i `changefreq` - wyższy dla nowszych postów
  ```python
  def priority(self, obj):
      age_days = (now() - obj.publish).days
      return 0.9 if age_days < 30 else (0.7 if age_days < 180 else 0.5)
  ```
- [ ] Dodać sitemap dla kategorii i tagów

**Pliki:** `apps/blog/sitemaps.py`

---

### 4.2 robots.txt dla środowisk

- [ ] W widoku `robots_txt` (lub template): sprawdź `settings.DEBUG`
- [ ] Jeśli `DEBUG=True`: `Disallow: /`
- [ ] Jeśli `DEBUG=False`: normalne reguły

**Pliki:** `templates/robots.txt` lub `apps/blog/views.py`

---

### 4.3 Canonical URLs przy paginacji

- [ ] W `PostListView.get_context_data`: jeśli `page > 1`, canonical = strona 1
- [ ] Dodać `rel="next"` / `rel="prev"` w `<head>`

**Pliki:** `apps/blog/views.py`, `templates/base.html`

---

### 4.4 Core Web Vitals

- [ ] Uruchomić Lighthouse na `/` i `/blog/<post>/`
- [ ] Naprawić LCP: `loading="eager"` + `fetchpriority="high"` na hero image
- [ ] Sprawdzić CLS: wymiary `width/height` na wszystkich `<img>`
- [ ] Font: sprawdzić czy `font-display: swap` jest ustawiony (już jest w Google Fonts URL)
- [ ] Zminifikować CSS/JS (lub dodać `whitenoise` z kompresją)

---

## Etap 5 - Testy

### Struktura

```
apps/
  blog/
    tests/
      __init__.py
      test_models.py       # Post, Comment, Category, Reaction, Bookmark
      test_views.py        # list, detail, search, author panel, reactions
      test_feeds.py        # RSS
      test_api.py          # DRF endpoints
  accounts/
    tests/
      __init__.py
      test_auth.py         # register, login, logout, password reset
      test_2fa.py          # setup, verify, backup codes, disable
      test_profile.py      # edit, public profile, bookmarks
      test_middleware.py   # TwoFactorMiddleware, rate limiting
```

### Priorytety testów

**Krytyczne (pisać pierwsze):**
- [ ] Rejestracja → weryfikacja e-mail → aktywacja → login
- [ ] Login z 2FA - poprawny kod, zły kod, backup code
- [ ] Rate limiting - po 5 próbach zwraca 429
- [ ] Blokada konta po nieudanych loginach
- [ ] Sanityzacja XSS w komentarzach
- [ ] Toggle reakcji - idempotentny (klik dwa razy = 0 reakcji)
- [ ] Newsletter - subscribe, confirm, unsubscribe, wysyłka po publikacji

**Ważne:**
- [ ] Widoki autora - tylko własne posty, brak dostępu do cudzych
- [ ] API - tokeny, uprawnienia, serializacja
- [ ] Komentarze - moderacja (active=False), paginacja

**Narzędzia:**
- `pytest-django` - już w projekcie
- `factory_boy` - fabryki modeli zamiast ręcznego tworzenia obiektów
- `django-webtest` lub `pytest`'s `Client` - testy widoków
- Coverage: cel >80%

---

## Kolejność wdrożenia

| Krok | Etap | Szacowany czas | Zależności |
|------|------|----------------|------------|
| 1 | 1.1 Sanityzacja komentarzy | 30 min | - |
| 2 | 1.6 Session timeout | 15 min | - |
| 3 | 4.2 robots.txt | 20 min | - |
| 4 | 2.1 Reset hasła | 1h | - |
| 5 | 2.8 Czas aktywności | 15 min | - |
| 6 | 4.3 Canonical paginacja | 30 min | - |
| 7 | 3.2 Dark/Light mode | 1.5h | - |
| 8 | 1.2 Weryfikacja e-maila | 2h | działający e-mail |
| 9 | 2.2 Powiadomienie o komentarzu | 1h | 1.2 |
| 10 | 2.5 Newsletter | 3h | 1.2 |
| 11 | 1.3 Rate limiting | 1h | - |
| 12 | 1.4 django-axes | 1h | - |
| 13 | 1.5 Backup codes 2FA | 2h | - |
| 14 | 1.7 Audit log | 2h | - |
| 15 | 2.3 Reakcje + views_count | 2h | - |
| 16 | 2.4 Zakładki | 1.5h | - |
| 17 | 2.7 Paginacja komentarzy | 1h | - |
| 18 | 3.1 Spis treści | 2h | - |
| 19 | 2.6 Panel autora | 4h | - |
| 20 | 4.1 Sitemap priorytety | 1h | - |
| 21 | 4.4 Core Web Vitals | 2h | Lighthouse |
| 22 | 5 Testy | 8h | wszystkie powyższe |

**Łącznie: ~40h roboczych**

---

## Wymagania zewnętrzne

- Backend e-mail (SMTP) - niezbędny dla: weryfikacja e-mail, reset hasła, newsletter, powiadomienia
  - Dev: `EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'` (już jest)
  - Prod: SendGrid / Mailgun / AWS SES - ustawić przez `.env`
- `django-ratelimit` - rate limiting
- `django-axes` - blokada loginów
- `factory_boy` - testy
- `pytest-cov` - coverage raport
- Opcjonalnie: Redis - dla cachowania i rate limitingu per-IP w produkcji
