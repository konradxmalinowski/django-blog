# Security & SEO Audit - DevLog - 2026-05-23

**Agent**: security-agent-sonnet (routine scope)
**Scope**: Full codebase read - settings, views, models, middleware, templates, API, serializers, URLs, requirements
**Stack**: Python 3.14, Django 5.2.14, SQLite (dev), DRF 3.17.1, bleach 6.3.0, pyotp 2.9.0, django-axes 8.3.1, django-ratelimit 4.1.0

---

## Executive Summary

The application demonstrates a mature security posture for a personal/portfolio project: 2FA TOTP with backup codes, email verification, brute-force protection (django-axes), rate limiting, bleach XSS sanitization, CSRF on all state-changing forms, and a solid set of security headers. The main risk areas are:

1. An open redirect in the 2FA verification flow that can be exploited to redirect users to external sites after login.
2. Missing production settings file - `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, and HSTS are not configured, meaning sessions and CSRF tokens travel in plaintext over HTTP if the production deployment does not patch these.
3. The `render_toc` template tag builds HTML from Markdown headings without sanitising the heading text before injecting into `mark_safe` output.
4. `django-axes` and `django-ratelimit` are absent from `requirements/base.txt`, risking silent omission in production images.
5. Several medium-severity gaps: no rate limit on 2FA verify or newsletter subscribe; backup codes use SHA-256 (non-HMAC, timing-attack risk); subscriber notification fires on every `save()` call, not just creation.

Total: 12 findings - Critical: 0 | High: 2 | Medium: 5 | Low: 3 | Info: 2

---

## Security Findings

### CRITICAL

None found.

---

### HIGH

#### [SEC-001] Open Redirect in `verify_2fa` - HIGH
**Category**: Broken Authentication / Unvalidated Redirect
**Location**: `apps/accounts/views.py:257-271`

```python
next_url = request.GET.get('next') or request.POST.get('next') or '/'
# ...
return redirect(next_url)
```

`next_url` is accepted from GET/POST and passed directly to `redirect()` without validation. Django's `redirect()` passes relative URLs through `HttpResponseRedirect`, but if `next_url` is an absolute URL like `https://evil.com`, the browser follows it without warning.

**Reproduction**:
```
GET /accounts/2fa/verify/?next=https://evil.com
```
After a valid TOTP code is entered, the user is sent to `https://evil.com`.

**Impact**: Phishing - attacker sends a login link, victim completes 2FA, lands on an attacker-controlled page.

**Fix**: Validate `next_url` using Django's built-in `url_has_allowed_host_and_scheme`:
```python
from django.utils.http import url_has_allowed_host_and_scheme

next_url = request.GET.get('next') or request.POST.get('next') or '/'
if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
    next_url = '/'
```

---

#### [SEC-002] Missing Production HTTPS Settings (No `production.py`) - HIGH
**Category**: Sensitive Data Exposure / Insecure Transport
**Location**: `devlog/settings/` (file missing), `devlog/settings/base.py`

`SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_SSL_REDIRECT`, and `SECURE_HSTS_SECONDS` are nowhere in the codebase. Only `local.py` extends `base.py`. There is no `production.py`. Without these settings:

- Session cookies are sent over plain HTTP.
- CSRF cookies are sent over plain HTTP.
- No HSTS header is emitted.

The `devlog/middleware.py` comment acknowledges this ("Nie ustawiamy HSTS lokalnie") but there is no production override that does set it.

**Impact**: Session hijacking, CSRF token interception, and MITM attacks are possible against production deployments served over HTTPS behind a proxy.

**Fix**: Create `devlog/settings/production.py`:
```python
from .base import *

DEBUG = False
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
```

---

### MEDIUM

#### [SEC-003] `render_toc` Injects Unsanitised Markdown Heading Text - MEDIUM
**Category**: XSS (Stored)
**Location**: `apps/blog/templatetags/blog_tags.py:58-80`

```python
items.append(
    f'<li class="{indent}"><a href="#{anchor}" class="toc-link">{text}</a></li>'
)
# ...
return mark_safe(html)
```

`text` is the raw heading string extracted from post body Markdown. If a post contains a heading like `## <img src=x onerror=alert(1)>`, `text` will be `<img src=x onerror=alert(1)>` and it is injected verbatim into the HTML returned via `mark_safe`. The `markdownify` filter runs bleach, but `render_toc` does not.

**Reproduction**: As an authenticated author, create a post with body:
```markdown
## <script>alert(1)</script>
## Normal heading
## Another heading
```
Three headings trigger ToC rendering; the first injects raw HTML into the ToC.

**Impact**: Stored XSS against any visitor of the affected post. Scope is limited to authors who can publish posts.

**Fix**: Escape `text` before interpolation:
```python
from django.utils.html import escape
items.append(
    f'<li class="{indent}"><a href="#{anchor}" class="toc-link">{escape(text)}</a></li>'
)
```

---

#### [SEC-004] Backup Code Verification Vulnerable to Timing Attacks - MEDIUM
**Category**: Authentication Weakness
**Location**: `apps/accounts/models.py:75-83`

```python
code_hash = hashlib.sha256(code.strip().upper().encode()).hexdigest()
try:
    backup = cls.objects.get(user=user, code_hash=code_hash, used=False)
```

SHA-256 hex-digest comparison happens inside the ORM `.get()` at the database level, which uses a standard equality check (not constant-time). An attacker with a database timing oracle (local/cloud timing side-channel) can, in theory, enumerate code hashes one character at a time.

**Impact**: Low practical exploitability for an external attacker, but the comparison should be constant-time per best practice. Larger concern is the use of bare SHA-256 (not HMAC or bcrypt) for secret code storage - a DB dump exposes codes directly reversible by brute force (codes are 5-byte hex = 10 hex chars = ~10^10 space, feasible on GPU).

**Fix**: Use `secrets.compare_digest` after fetching the candidate row, or store codes hashed with `hashlib.pbkdf2_hmac` / `django.contrib.auth.hashers.make_password`. Minimum: add salt per-user.

---

#### [SEC-005] No Rate Limit on 2FA Verification Endpoint - MEDIUM
**Category**: Broken Authentication / Brute Force
**Location**: `apps/accounts/views.py:249` (`verify_2fa` view)

`verify_2fa` has no `@ratelimit` decorator and no django-axes integration (axes only tracks the primary login view). An attacker who obtains a valid session (e.g., via session fixation or a stolen cookie) can brute-force the 6-digit TOTP window. The TOTP window is 30 seconds (±1 step by default in pyotp), giving 3 valid codes per minute, but the endpoint accepts unlimited attempts.

**Reproduction**: Send POST to `/accounts/2fa/verify/` with sequential `code` values in a loop.

**Fix**:
```python
@ratelimit(key='user', rate='5/m', method='POST', block=True)
def verify_2fa(request):
```
Also log failed 2FA attempts via `log_action` (currently done - SEC-INFO) and consider adding axes lockout here too.

---

#### [SEC-006] Newsletter Subscribe Has No Rate Limiting and No Email Validation - MEDIUM
**Category**: Abuse / Spam / Resource Exhaustion
**Location**: `apps/blog/views.py:276-287`

```python
def newsletter_subscribe(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        if email:
            sub, created = Subscriber.objects.get_or_create(email=email)
```

- No `@ratelimit` - an attacker can submit arbitrary emails at full speed.
- `email` is taken directly from `request.POST` with only `.strip()`, no `EmailValidator` call.
- If a valid email is submitted repeatedly, `get_or_create` suppresses duplicates, but the confirm email is only sent on `created=True`, so spam impact is limited. However, invalid/non-email strings pass into the DB as `Subscriber.email` (which is an `EmailField` at the model level but not enforced here at the view level before the DB call).
- `HTTP_REFERER` redirect is used for the redirect target - low risk but still an unvalidated header.

**Fix**:
```python
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

@ratelimit(key='ip', rate='5/h', method='POST', block=True)
def newsletter_subscribe(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip()
        try:
            validate_email(email)
        except ValidationError:
            messages.error(request, 'Nieprawidłowy adres e-mail.')
            return redirect('blog:post_list')
        ...
```

---

#### [SEC-007] `notify_subscribers` Signal Fires on Every `post.save()`, Not Just Publication - MEDIUM
**Category**: Logic Flaw / Email Abuse
**Location**: `apps/blog/models.py:190-206`

```python
@receiver(post_save, sender=Post)
def notify_subscribers(sender, instance, **kwargs):
    if instance.status == 'published':
        ...
        for sub in subscribers:
            send_mail(...)
```

The signal fires on every `.save()` call where `status='published'`, including edits to already-published posts (typo fix, cover image update, etc.). This sends a duplicate notification email to all confirmed subscribers each time a published post is saved.

**Fix**: Check `kwargs.get('created')` or compare `instance.status` against the previous value using `update_fields` or a pre-save hook:
```python
@receiver(post_save, sender=Post)
def notify_subscribers(sender, instance, created, **kwargs):
    if created and instance.status == 'published':
        ...
```
Or, more robustly, track `was_published` via a `pre_save` signal.

---

### LOW

#### [SEC-008] Trusted IP Extraction Without Proxy Whitelist (`HTTP_X_FORWARDED_FOR`) - LOW
**Category**: IP Spoofing / Auth Bypass
**Location**: `apps/accounts/utils.py:1-5`

```python
x_forwarded = request.META.get('HTTP_X_FORWARDED_FOR')
if x_forwarded:
    return x_forwarded.split(',')[0].strip()
```

`X-Forwarded-For` can be set by any client; the leftmost IP is user-controlled if there is no trusted proxy stripping it. This IP is used in `AuditLog` and for `django-axes` lockout tracking. A malicious user can spoof their IP in audit logs or defeat axes lockout by cycling values in the `X-Forwarded-For` header.

**Fix**: Configure Django's `SECURE_PROXY_SSL_HEADER` and use axes's built-in IP resolution (`AXES_PROXY_COUNT` / `AXES_META_PRECEDENCE_ORDER`) instead of custom IP extraction. For audit logs, either trust only the last IP (set by a known trusted proxy) or use `request.META['REMOTE_ADDR']` if a proxy is not involved.

---

#### [SEC-009] Security Packages (`django-axes`, `django-ratelimit`, `pyotp`) Missing from `requirements/base.txt` - LOW
**Category**: Supply Chain / Deployment Risk
**Location**: `requirements/base.txt`, `requirements/local.txt`

`django-axes`, `django-ratelimit`, and `pyotp` are installed in the project venv (confirmed: axes 8.3.1, ratelimit 4.1.0, pyotp 2.9.0) but none appear in any requirements file. A fresh production deployment from `requirements/production.txt` will succeed at `pip install` but fail at runtime with `ImportError` when the middleware or decorators are first called.

**Fix**: Add to `requirements/base.txt`:
```
django-axes>=8.3
django-ratelimit>=4.1
pyotp>=2.9
qrcode>=7.0
```

---

#### [SEC-010] `DEFAULT_FROM_EMAIL` Uses `noreply@devlog.local` - LOW
**Category**: Email / Phishing Risk
**Location**: `devlog/settings/base.py:124`, `apps/blog/views.py:206`, `apps/blog/models.py:198`

Several `send_mail` calls hard-code `'devlog@example.com'` as the sender rather than using `settings.DEFAULT_FROM_EMAIL`. The domain `example.com` is IANA-reserved and will cause SPF/DKIM failures in production, marking outgoing mail as spam or causing delivery failure.

**Fix**: Replace all hard-coded `'devlog@example.com'` strings with `settings.DEFAULT_FROM_EMAIL` and configure a real domain in production `.env`.

Affected files:
- `apps/blog/views.py:186, 206, 309`
- `apps/blog/models.py:198`

---

### INFO / Good Practices Found

#### [SEC-INFO-001] Strong Security Header Stack
`devlog/middleware.py` (SecurityHeadersMiddleware) correctly sets `Content-Security-Policy`, `Permissions-Policy`, `Referrer-Policy`, `X-Content-Type-Options`, and `X-Frame-Options` on every response. The CSP uses `'unsafe-inline'` for scripts and styles (required for the terminal JS effects and Google Fonts), which is acceptable for a blog with no sensitive authenticated actions beyond the admin.

#### [SEC-INFO-002] 2FA, Backup Codes, Email Verification, Audit Log - Well Implemented
- TOTP secret generated with `pyotp.random_base32()` (128-bit entropy - correct).
- Backup codes use `secrets.token_hex(5)` (cryptographically random - correct).
- Email verification tokens use `uuid.uuid4` (correct, and tokens expire in 24h).
- `AuditLog` records all sensitive account events with IP and User-Agent.
- `django-axes` provides brute-force lockout (5 failures / 1 hour cooldown).
- `update_session_auth_hash` called on password change (prevents session invalidation attack).
- `bleach.clean()` applied to comment bodies in `CommentForm.clean_body()` and to Markdown output in the `markdownify` filter.

---

## SEO Findings

### Issues

#### [SEO-001] `<title>` Tag Double-Appends "| DevLog"
**Location**: `templates/base.html:8`

```html
<title>{% block title %}{{ SITE_NAME|default:"DevLog" }}{% endblock %} | DevLog</title>
```

On the post detail page, `{% block title %}` renders `"{{ post.title }} - devlog"` (from `post_detail.html:4`), resulting in: `"My Post - devlog | DevLog"` - the brand name appears twice and the separator is inconsistent (`-` vs `|`).

**Fix**: Either remove `| DevLog` from `base.html` and always include the brand in the block, or use a `title_raw` / `title_suffix` pattern:
```html
<title>{% block page_title %}{{ SITE_NAME|default:"DevLog" }}{% endblock %}</title>
```
And in `post_detail.html`: `{% block page_title %}{{ post.title }} | DevLog{% endblock %}`.

---

#### [SEO-002] Canonical URL Relies on `{{ SITE_URL }}{{ request.path }}` - May Include Query Strings
**Location**: `templates/base.html:15`

```html
<link rel="canonical" href="{% block canonical_url %}{{ SITE_URL }}{{ request.path }}{% endblock %}">
```

`request.path` does not include query strings (correct), but paginated list views include `?page=N` in the URL while the canonical points to the base path - only correct if Google respects the canonical over the actual URL. However, the comment-pagination in `post_detail.html` uses `?comment_page=N`, which means all comment pages share the same canonical as the main post detail page. This is actually correct SEO behaviour, but worth confirming intentionally.

Larger issue: on list views (tag, category, author), `SITE_URL` is set to `https://devlog.example.com` globally, so in local dev (`SITE_URL = 'http://127.0.0.1:8000'`) the canonical points to localhost. The dynamic canonical should use `request.build_absolute_uri(request.path)` instead of `SITE_URL` concatenation to avoid environment bleed.

**Fix**:
```html
<link rel="canonical" href="{% block canonical_url %}{{ request.build_absolute_uri }}{% endblock %}">
```
Override in post_detail.html with the post's actual canonical URL.

---

#### [SEO-003] `og:image` Is Empty for Posts Without a Cover Image
**Location**: `templates/base.html:25`, `templates/blog/post_detail.html:11`

```html
<meta property="og:image" content="{% block og_image %}{{ SITE_DEFAULT_IMAGE|default:'' }}{% endblock %}">
```

`SITE_DEFAULT_IMAGE = ''` in `base.py` and `TWITTER_HANDLE = ''`. When sharing a post without a cover image on social media, the `og:image` tag is empty, resulting in a blank/missing card preview. Facebook and Twitter/X significantly reduce engagement for posts without preview images.

**Fix**: Set a real fallback OG image in settings:
```python
SITE_DEFAULT_OG_IMAGE = '/static/img/devlog-og-default.png'  # 1200x630px
```
Or generate a text-based fallback dynamically.

---

#### [SEO-004] `robots.txt` Blocks `/search/` But the App Uses `/search/?query=...`
**Location**: `templates/robots.txt:10`

```
Disallow: /search/
```

The search endpoint is actually at `/` via `blog:post_search` which maps to a path in `blog/urls.py`. If the path is `/search/`, this is intentional (good - blocks search result pages from indexing). But `Disallow: /*?page=*` uses a wildcard pattern that only Googlebot understands; Bingbot and other crawlers may not honour `*` wildcards consistently.

**Fix**: Add explicit Disallow lines for common paginated patterns alongside the wildcard:
```
Disallow: /*?page=
Disallow: /*?comment_page=
```

---

#### [SEO-005] Sitemap `protocol = 'https'` But Dev `SITE_URL` Is `http://127.0.0.1:8000`
**Location**: `apps/blog/sitemaps.py:9`

All three Sitemap classes hard-code `protocol = 'https'`. This means the sitemap always generates `https://` URLs regardless of the actual site URL. In production this is correct and intentional. In dev/staging with HTTP, the sitemap will return URLs that do not match the actual server. This is a minor config hygiene issue, not a production SEO problem.

---

#### [SEO-006] Missing `<link rel="alternate" type="application/rss+xml">` for Per-Category Feeds
**Location**: `templates/base.html:66`

```html
<link rel="alternate" type="application/rss+xml" title="{{ SITE_NAME|default:'DevLog' }} RSS" href="{% url 'blog:post_feed' %}">
```

Only the global RSS feed is declared. If category feeds exist (`blog:category_feed`), they are not discoverable via `<link rel="alternate">` from category listing pages. This reduces feed reader auto-discovery for category-specific content.

**Fix**: In `CategoryPostListView`'s template, add:
```html
{% block extra_head %}
<link rel="alternate" type="application/rss+xml"
      title="{{ SITE_NAME }} - {{ category.name }}" 
      href="{% url 'blog:category_feed' category.slug %}">
{% endblock %}
```

---

### Recommendations

#### SEO Positive Signals (keep these)
- Dynamic `priority` and `changefreq` in `PostSitemap` based on post age - well thought out.
- `BlogPosting` + `BreadcrumbList` JSON-LD structured data in `post_detail.html` - complete and correct.
- `WebSite` + `SearchAction` JSON-LD in `base.html` - enables Google's sitelinks search box.
- `<time datetime="{{ post.publish|date:'c' }}">` - correct ISO 8601 machine-readable date.
- `hreflang="pl"` + `hreflang="x-default"` present - good for monolingual international SEO.
- `<meta name="keywords">` is present (low SEO value today, but harmless).
- Sitemap linked in both `robots.txt` and `<footer>`.
- `paginate_by = 3` in `PostListView` produces short, fast-loading list pages.

---

## Action Items

Priority order (fix before production launch):

1. **[SEC-001] - HIGH** Fix open redirect in `verify_2fa`: add `url_has_allowed_host_and_scheme` validation on `next_url`. One-line fix.

2. **[SEC-002] - HIGH** Create `devlog/settings/production.py` with `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `SECURE_SSL_REDIRECT`, `SECURE_HSTS_SECONDS`. Without this, production HTTPS is partial.

3. **[SEC-009] - LOW (deployment blocker)** Add `django-axes`, `django-ratelimit`, `pyotp`, `qrcode` to `requirements/base.txt`. Without this, a fresh `pip install -r requirements/production.txt` will produce a broken application.

4. **[SEC-003] - MEDIUM** Escape heading text in `render_toc` with `django.utils.html.escape(text)` before `mark_safe`. One-line fix.

5. **[SEC-005] - MEDIUM** Add `@ratelimit(key='user_or_ip', rate='5/m', method='POST', block=True)` to `verify_2fa`.

6. **[SEC-006] - MEDIUM** Add `@ratelimit` and `EmailValidator` to `newsletter_subscribe`.

7. **[SEC-007] - MEDIUM** Guard `notify_subscribers` signal with `if created and instance.status == 'published'` or a pre-save check to prevent duplicate subscriber emails on post edits.

8. **[SEC-004] - MEDIUM** Upgrade backup code hashing to use `hashlib.pbkdf2_hmac` with a per-user salt, or use `django.contrib.auth.hashers.make_password` / `check_password`.

9. **[SEC-010] - LOW** Replace all `'devlog@example.com'` hard-coded senders with `settings.DEFAULT_FROM_EMAIL` and configure a real domain in `.env`.

10. **[SEC-008] - LOW** Review `get_client_ip` proxy header trust logic; use `AXES_META_PRECEDENCE_ORDER` for axes rather than a custom util.

11. **[SEO-001]** Fix double "DevLog" in `<title>` tag.

12. **[SEO-002]** Use `request.build_absolute_uri(request.path)` for canonical URL instead of `SITE_URL` concatenation.

13. **[SEO-003]** Set a real `SITE_DEFAULT_OG_IMAGE` (1200x630 PNG/JPG) for social sharing fallback.

14. **[SEO-006]** Add per-category `<link rel="alternate" type="application/rss+xml">` in category listing template.
