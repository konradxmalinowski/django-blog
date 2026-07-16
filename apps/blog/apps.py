from django.apps import AppConfig


class BlogConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.blog'
    label = 'blog'

    def ready(self):
        from django.db.models.signals import post_migrate
        post_migrate.connect(_bootstrap, sender=self)


def _bootstrap(sender, **kwargs):
    import sys
    if 'pytest' in sys.modules:
        return
    _ensure_superuser()
    _ensure_sample_posts()


def _ensure_superuser():
    from django.conf import settings
    from django.contrib.auth.models import User

    username = getattr(settings, 'SUPERUSER_USERNAME', '')
    email    = getattr(settings, 'SUPERUSER_EMAIL', '')
    password = getattr(settings, 'SUPERUSER_PASSWORD', '')

    if not username or not password:
        return

    if not User.objects.filter(username=username).exists():
        User.objects.create_superuser(username=username, email=email, password=password)
        print(f'[devlog] Superuser "{username}" created.')


def _ensure_sample_posts():
    from django.contrib.auth.models import User
    from django.conf import settings
    from apps.blog.models import Category, Post

    if Post.objects.exists():
        return

    username = getattr(settings, 'SUPERUSER_USERNAME', '') or 'admin'
    author = (
        User.objects.filter(username=username).first()
        or User.objects.filter(is_superuser=True).first()
    )
    if not author:
        return

    categories = [
        ('Backend',  'backend',  '#7ee787'),
        ('Frontend', 'frontend', '#79c0ff'),
        ('DevOps',   'devops',   '#ffa657'),
    ]
    cat_objs = {}
    for name, slug, color in categories:
        cat, _ = Category.objects.get_or_create(slug=slug, defaults={'name': name, 'color': color})
        cat_objs[slug] = cat

    sample_posts = [
        {
            'title': 'Cykl tworzenia aplikacji webowej - wstęp',
            'slug': 'cykl-tworzenia-aplikacji-webowej-wstep',
            'category': 'backend',
            'excerpt': 'Każdy projekt zaczyna się od decyzji. Dlaczego Django, dlaczego Python 3.14 i jak wygląda cały cykl.',
            'body': """## Dlaczego Django?

Django to framework z podejściem „batteries included". Wszystko czego potrzebuje typowa aplikacja webowa jest dostępne od razu - ORM, panel admina, system szablonów, autentykacja.

### Python 3.14

Python 3.14 wprowadza szereg optymalizacji wydajnościowych. Projekt działa na nim bez żadnych modyfikacji.

## Plan

Cykl tworzenia tej aplikacji podzielony jest na 7 faz:

1. **Core** - modele, widoki, szablony
2. **Email i komentarze** - udostępnianie postów, system komentarzy
3. **Template tags** - własne tagi, sidebar widgets
4. **Konta użytkowników** - rejestracja, logowanie, profile
5. **RSS i sitemap** - kanały RSS, mapa strony
6. **REST API** - Django REST Framework, tokeny
7. **UI polish** - terminal CSS, dark/light mode, animacje
""",
            'tags': ['django', 'python', 'webdev'],
        },
        {
            'title': 'Modele Django - Post, Category, Comment',
            'slug': 'modele-django-post-category-comment',
            'category': 'backend',
            'excerpt': 'Projektowanie modeli to fundament. Omawiam decyzje dotyczące struktury Post, Category i Comment.',
            'body': """## Model Post

Kluczowe decyzje projektowe:

- `slug` z `unique_for_date='publish'` - ten sam slug może wystąpić w różnych dniach
- `MarkdownxField` zamiast TextField - wbudowany podgląd w adminie
- `PublishedManager` - osobny manager dla opublikowanych postów

```python
class PublishedManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(status='published')
```

## Model Category

Prosta struktura: nazwa, slug, opis, kolor. Bez zagnieżdżania - blog jest płaski.

## Model Comment

Komentarze są moderowane (`active=False` domyślnie). Pole `user` jest opcjonalne - komentować mogą niezalogowani.

### XSS sanitization

Treść komentarza jest sanityzowana przez `bleach` przed zapisem:

```python
def clean_body(self):
    return bleach.clean(self.cleaned_data['body'],
                        tags=ALLOWED_TAGS, strip=True)
```
""",
            'tags': ['django', 'models', 'orm'],
        },
        {
            'title': 'Terminal CSS - budowanie dark theme od zera',
            'slug': 'terminal-css-budowanie-dark-theme',
            'category': 'frontend',
            'excerpt': 'Jak zbudować spójny terminal-style design system używając CSS custom properties bez żadnego frameworka.',
            'body': """## Design system w CSS

Cały motyw oparty jest na CSS custom properties. Dzięki temu przełączanie dark/light mode to zmiana kilku tokenów:

```css
:root {
  --bg:           #0d1117;
  --accent-green: #00ff41;
}

.light-mode {
  --bg:           #f6f8fa;
  --accent-green: #1a7f37;
}
```

## ASCII box components

Karty używają znaków box-drawing zamiast zwykłych borderów - czysty CSS, zero obrazków.

## JetBrains Mono

Font monospace ładowany z Google Fonts. Fallback: Fira Code, Cascadia Code, Consolas.

### Responsive

Na mobile navbar zwija się, sidebar znika - content zajmuje pełną szerokość.
""",
            'tags': ['css', 'design', 'frontend'],
        },
        {
            'title': 'REST API z Django REST Framework',
            'slug': 'rest-api-django-rest-framework',
            'category': 'backend',
            'excerpt': 'Budowanie REST API z TokenAuthentication, serializatorami i permissions - krok po kroku.',
            'body': """## Dlaczego DRF?

Django REST Framework to standard dla REST API w Django. Serializatory, widoki generyczne i system uprawnień działają spójnie.

## Endpointy

| Metoda | URL | Opis |
|--------|-----|------|
| GET/POST | `/api/posts/` | Lista + tworzenie |
| GET/PUT/DELETE | `/api/posts/<slug>/` | Szczegóły |
| POST | `/api/auth/token/` | Token auth |

## TokenAuthentication

```python
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
    ],
}
```

Token przekazywany w nagłówku: `Authorization: Token <token>`.

## Permissions

Autor może edytować tylko własne posty - custom permission `IsAuthorOrReadOnly`.
""",
            'tags': ['api', 'drf', 'django'],
        },
        {
            'title': 'Bezpieczeństwo - 2FA, rate limiting, django-axes',
            'slug': 'bezpieczenstwo-2fa-rate-limiting-django-axes',
            'category': 'backend',
            'excerpt': 'Warstwa bezpieczeństwa: weryfikacja email, TOTP 2FA, kody zapasowe, blokada brute-force i audit log.',
            'body': """## Email verification

Nowi użytkownicy rejestrują się z `is_active=False`. Token UUID wysyłany emailem aktywuje konto. Token wygasa po 24h.

## TOTP 2FA

Implementacja z biblioteką `pyotp`. Użytkownik skanuje QR code w Google Authenticator / Authy.

```python
import pyotp
totp = pyotp.TOTP(profile.totp_secret)
if totp.verify(code):
    request.session['2fa_verified'] = True
```

## Kody zapasowe

8 jednorazowych kodów, hashowanych SHA-256. Pozwalają zalogować się bez aplikacji TOTP.

## django-axes

Blokada po 5 nieudanych próbach logowania. Cooldown 1 godzina. Reset po sukcesie.

## Audit log

Każda akcja security (login, logout, zmiana hasła, 2FA on/off) zapisywana do modelu `AuditLog` z IP i User-Agent.
""",
            'tags': ['security', '2fa', 'django'],
        },
    ]

    for data in sample_posts:
        Post.objects.create(
            title=data['title'],
            slug=data['slug'],
            author=author,
            category=cat_objs.get(data['category']),
            body=data['body'],
            excerpt=data['excerpt'],
            status='published',
        )

    print(f'[devlog] {len(sample_posts)} sample posts created.')
