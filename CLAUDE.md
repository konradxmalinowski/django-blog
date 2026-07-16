# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project: DevLog - Blog „Cykl tworzenia aplikacji webowej"

Django blog z terminal-style UI. Każdy post dokumentuje jeden etap cyklu tworzenia aplikacji webowej.

## Stack

- Python 3.14, Django 5.2 (4.2 LTS nie obsługuje Python 3.14)
- SQLite (dev) - PostgreSQL-ready
- django-taggit, djangorestframework, django-markdownx, Pillow, bleach, python-decouple
- Terminal CSS (własny) + Vanilla JS

## Commands

```bash
# Aktywacja venv
source .venv/bin/activate

# Serwer dev
DJANGO_SETTINGS_MODULE=devlog.settings.local python manage.py runserver

# Migracje
python manage.py makemigrations
python manage.py migrate

# Shell
python manage.py shell

# Superuser
python manage.py createsuperuser

# Static files
python manage.py collectstatic
```

## Project Structure

```
DjangoProject/
├── devlog/                  ← konfiguracja projektu
│   ├── settings/
│   │   ├── base.py          ← wspólne ustawienia
│   │   └── local.py         ← dev (DEBUG=True, SQLite, email konsola)
│   └── urls.py              ← główny router
├── apps/
│   ├── blog/                ← posty, komentarze, tagi, kategorie
│   ├── accounts/            ← UserProfile, rejestracja, profil
│   └── api/                 ← DRF REST API
├── templates/               ← wszystkie szablony Django (tu, nie w apps/)
│   ├── base.html
│   ├── partials/            ← navbar, footer, sidebar, pagination
│   ├── blog/
│   └── accounts/
├── static/
│   ├── css/terminal.css     ← terminal theme (dark, monospace, ASCII-box)
│   └── js/terminal.js
├── media/                   ← przesyłane pliki (obrazy postów, avatary)
├── plans/                   ← plany implementacji
├── errors/                  ← błędy wymagające decyzji
└── reports/                 ← raporty security/quality
```

## Django Apps

Wszystkie apps są w `apps/` z prefiksem w INSTALLED_APPS:
```python
'apps.blog'     # label='blog'
'apps.accounts' # label='accounts'
'apps.api'      # label='api'
```

Import modeli: `from apps.blog.models import Post, Category, Comment`

## Key Models

**blog.Post** - title, slug (unique_for_date='publish'), author (FK User), category (FK Category), body (Markdown), excerpt, cover_image, tags (TaggableManager), publish, status ('draft'/'published'), reading_time

**blog.Category** - name, slug, description, color

**blog.Comment** - post (FK), user (FK nullable), name, email, body, active

**accounts.UserProfile** - OneToOne User, bio, avatar, github_url, website (auto-created via post_save signal)

## URL Namespaces

- `blog:post_list`, `blog:post_detail`, `blog:post_share`, `blog:post_search`
- `blog:post_list_by_tag`, `blog:post_list_by_category`, `blog:post_list_by_author`
- `blog:post_feed` (RSS globalny), `blog:category_feed` (RSS per-category)
- `accounts:register`, `accounts:login`, `accounts:logout`, `accounts:profile`
- `api:` - DRF API root

## API

DRF z TokenAuthentication. Endpointy:
- GET/POST `/api/posts/` - lista + tworzenie (auth)
- GET/PUT/PATCH/DELETE `/api/posts/<slug>/` - szczegóły + edycja (author/admin)
- GET/POST `/api/posts/<slug>/comments/` - komentarze
- GET `/api/tags/`, `/api/categories/`
- POST `/api/auth/token/` - uzyskanie tokenu

## Terminal UI Design

Paleta CSS (tokens w terminal.css):
- `--bg: #0d1117`, `--bg-card: #161b22`, `--bg-border: #30363d`
- `--text-primary: #c9d1d9`, `--text-secondary: #8b949e`
- `--accent-green: #7ee787` (komendy, nagłówki)
- `--accent-blue: #79c0ff` (linki, tagi)
- Font: 'JetBrains Mono', monospace

Komponenty: ASCII-box karty (┌─┐│└─┘), pseudoprompt breadcrumbs (`~/blog/posts$`), ASCII progress bar czasu czytania.

## Settings

Używaj zawsze `DJANGO_SETTINGS_MODULE=devlog.settings.local` na dev.
Zmienne z `.env` przez `python-decouple`. Plik `.env.example` zawiera wszystkie klucze.

## Hosting

Dwa równoległe cele wdrożenia produkcyjnego:

| Cel | Settings module | Requirements | Serwer aplikacji | Baza | Instrukcja |
|---|---|---|---|---|---|
| Render | `devlog.settings.production` | `requirements/production.txt` | gunicorn | PostgreSQL (`DATABASE_URL`) | `docs/07-render-hosting.md` |
| CT8 (MyDevil/Small.pl, Passenger) | `devlog.settings.ct8` | `requirements/ct8.txt` | Passenger (`passenger_wsgi.py`) | SQLite | `docs/08-ct8-hosting.md` |

Oba cele mają `DEMO_MODE=True` i dummy email backend - rejestracja jest natychmiastowa, bez realnej wysyłki maili.

## Conventions

- Szablony TYLKO w `templates/` (nie w apps/templates/)
- Widoki jako CBV (ListView, DetailView) lub FBV - nie mieszaj w obrębie jednej funkcji
- Markdown body postów - NIGDY nie renderuj bez bleach sanitize
- Komentarze do kodu: tylko gdy WHY jest nieoczywiste
- Testy: pytest, plik tests/ w każdej app

## Implementation Status

All 7 phases complete:

| Phase | Feature | Status |
|---|---|---|
| 1 | Core blog: Post/Category/Comment models, list/detail views, terminal CSS | ✅ |
| 2 | Email sharing, comment system, full-text search | ✅ |
| 3 | Custom template tags, sidebar widgets (recent, most commented, tag cloud) | ✅ |
| 4 | User accounts: UserProfile, register/login, public profiles | ✅ |
| 5 | RSS feeds (global + per-category), XML sitemap, robots.txt | ✅ |
| 6 | DRF REST API: posts, comments, categories, tags, token auth | ✅ |
| 7 | Terminal UI polish: CSS tokens, JS effects, responsive, JetBrains Mono | ✅ |
