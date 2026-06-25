<h1 align="center">DevLog</h1>
<p align="center">
  <img src="https://img.shields.io/badge/Python-3.14-3776AB?logo=python&logoColor=white" alt="Python 3.14">
  <img src="https://img.shields.io/badge/Django-5.2-092E20?logo=django&logoColor=white" alt="Django 5.2">
  <img src="https://img.shields.io/badge/DRF-REST_API-A30000?logo=django&logoColor=white" alt="Django REST Framework">
  <img src="https://img.shields.io/badge/SQLite-dev_|_PostgreSQL_ready-003B57?logo=sqlite&logoColor=white" alt="Database">
</p>
<p align="center">
  A developer blog documenting the full build cycle of a Django web application — terminal-style UI, REST API, two-factor authentication, newsletter, RSS, and comment moderation.
</p>

---

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Getting Started](#getting-started)
- [Testing](#testing)
- [Documentation](#documentation)

---

## Overview

DevLog is a full-featured Django blog built as a live record of its own development. Every layer of the stack is documented incrementally — from initial setup and data models through security hardening, REST API design, and frontend components. The UI uses a custom terminal dark theme with JetBrains Mono, no CSS framework.

---

## Features

- **REST API** — DRF-powered endpoints with token authorization; full curl reference in [`docs/04-api.md`](docs/04-api.md)
- **Two-factor authentication** — TOTP-based 2FA via `pyotp`; QR code enrollment flow built into the account panel
- **Brute-force & rate limiting** — `django-axes` lockout policy + `django-ratelimit` on sensitive views
- **Newsletter** — subscription management and broadcast from the author panel
- **RSS feed** — auto-generated feed for all published posts
- **Comment system** — threaded comments with author moderation queue
- **Author panel** — post management, comment moderation, newsletter dispatch, audit log
- **Security** — XSS sanitization via `bleach`, CSRF enforcement, Content Security Policy headers, full audit log
- **Dark / light mode** — system-aware theme toggle persisted in `localStorage`
- **Markdown editor** — `django-markdownx` with live preview; tags via `django-taggit`

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.14 |
| Framework | Django 5.2 |
| API | Django REST Framework |
| Database | SQLite (development) · PostgreSQL-ready |
| Content | django-markdownx, django-taggit |
| Auth / 2FA | Django auth + pyotp (TOTP) |
| Security | django-axes, django-ratelimit, bleach |
| Frontend | Custom terminal CSS, JetBrains Mono, Vanilla JS |
| Testing | pytest, pytest-django |

---

## Getting Started

### Prerequisites

- Python 3.14
- `pip` and `venv`
- SMTP credentials for email features (newsletter, 2FA backup codes)

### Installation

```bash
git clone <repo-url>
cd DjangoProject

python3.14 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate

pip install -r requirements/local.txt

cp .env.example .env
# Fill in SECRET_KEY, SUPERUSER_*, and EMAIL_* in .env
```

### Run

```bash
DJANGO_SETTINGS_MODULE=devlog.settings.local python manage.py migrate
# Superuser and sample posts are created automatically by a data migration

DJANGO_SETTINGS_MODULE=devlog.settings.local python manage.py runserver
```

| URL | Description |
|---|---|
| `http://127.0.0.1:8000` | Application |
| `http://127.0.0.1:8000/admin` | Django admin |
| `http://127.0.0.1:8000/api/` | REST API root |

Full setup reference (env vars, backups, logging): [`docs/01-setup.md`](docs/01-setup.md)

---

## Testing

```bash
DJANGO_SETTINGS_MODULE=devlog.settings.local venv/bin/pytest -v
```

---

## Documentation

| File | Contents |
|---|---|
| [`docs/01-setup.md`](docs/01-setup.md) | Installation, environment variables, tests, backup, logging |
| [`docs/02-architecture.md`](docs/02-architecture.md) | Stack, data models, URL namespaces, middleware |
| [`docs/03-security.md`](docs/03-security.md) | Brute-force protection, rate limiting, 2FA, XSS, CSRF, audit log |
| [`docs/04-api.md`](docs/04-api.md) | REST API — endpoints, authorization, curl examples |
| [`docs/05-frontend.md`](docs/05-frontend.md) | CSS design system, JS, dark/light mode, components |
| [`docs/06-features.md`](docs/06-features.md) | Comments, 2FA, newsletter, author panel, moderation |
