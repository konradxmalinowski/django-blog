# Plan: konfiguracja pod hosting CT8 (MyDevil/Small.pl, Passenger)

## Problem

Projekt ma już gotową konfigurację pod Render (`devlog/settings/production.py`, `render.yaml`, `build.sh`, gunicorn). Użytkownik chce dodatkowo wdrożyć na CT8 — hosting współdzielony oparty o Phusion Passenger (ten sam model co MyDevil/Small.pl). Passenger nie używa gunicorn ani `$PORT` — potrzebuje pliku `passenger_wsgi.py` w katalogu aplikacji, a interpreter Pythona (z virtualenv) i domenę ustawia się w panelu, nie w kodzie.

Render pozostaje bez zmian — to jest dodatkowa ścieżka wdrożenia, nie zamiana.

## Ustalenia z użytkownikiem

- Baza danych: SQLite (plik) — CT8 ma trwały filesystem, więc to bezpieczne, w przeciwieństwie do Render free tier.
- Statyki/media: WhiteNoise — Django serwuje je samo, bez ręcznej konfiguracji aliasów w panelu CT8.
- Email: demo mode (bez realnej wysyłki), tak jak obecnie na Render.
- Dane CT8 (login, domena): placeholdery w kodzie/dokumentacji — użytkownik uzupełni sam przy realnym wdrożeniu.

## Zakres zmian

1. `devlog/settings/ct8.py` — nowy moduł ustawień produkcyjnych pod Passenger/CT8:
   - `DEBUG=False`, WhiteNoise middleware + storage (jak w `production.py`)
   - baza: dziedziczy SQLite z `base.py` (bez `DATABASE_URL`/`dj_database_url` — niepotrzebne przy SQLite, oszczędza instalację `psycopg2` na współdzielonym hostingu)
   - logowanie do plików (`logs/django.log`, `logs/security.log`) — sensowne na CT8 dzięki trwałemu dyskowi (na Render był tylko console, bo tam liczy się stdout)
   - `SECURE_SSL_REDIRECT`, HSTS, `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE` — CT8 ma darmowe SSL (Let's Encrypt) z panelu
   - `DEMO_MODE=True`, `EMAIL_BACKEND` dummy
2. `passenger_wsgi.py` w katalogu głównym repo — wymagany przez Passenger, ustawia `DJANGO_SETTINGS_MODULE=devlog.settings.ct8` i eksportuje `application`.
3. `requirements/ct8.txt` — `base.txt` + `whitenoise`, bez `gunicorn`/`psycopg2-binary`/`dj-database-url` (niepotrzebne przy Passenger + SQLite).
4. `.env.ct8.example` — szablon zmiennych do pliku `.env` tworzonego ręcznie przez SSH na koncie CT8 (python-decouple czyta `.env` automatycznie, panel CT8 nie ma rozbudowanego UI na zmienne środowiskowe jak Render).
5. `docs/08-ct8-hosting.md` — instrukcja krok po kroku (wzorowana na `docs/07-render-hosting.md`): SSH + venv, panel CT8 (plik wykonywalny, środowisko, domena), `.env`, `passenger_wsgi.py`, `collectstatic`, `migrate`, restart (`touch tmp/restart.txt` — standard Passenger).
6. `CLAUDE.md` — dopisać sekcję o dostępnych celach hostingu (Render + CT8) i odpowiadających plikach.

## Co NIE wchodzi w zakres

- Żadnych zmian w logice aplikacji, modelach, widokach.
- Migracja z Render na CT8 (oba pozostają skonfigurowane równolegle).
- Automatyzacja deployu (CT8 nie ma natywnego CI/CD jak Render — deploy jest ręczny przez SSH/git pull na serwerze).

## Weryfikacja

- `python manage.py check --settings=devlog.settings.ct8` lokalnie (z `DEBUG=False`, testowym `SECRET_KEY`/`ALLOWED_HOSTS` w env) — upewnić się, że moduł się w ogóle importuje i nie ma błędów konfiguracji.
- Przegląd bezpieczeństwa ustawień produkcyjnych (SSL redirect, cookie flags, ALLOWED_HOSTS) — świadomie, bez pełnego security-agent audytu, bo to plik konfiguracyjny analogiczny do już zaakceptowanego `production.py`.

## Commit

Jeden commit: `feat: add CT8/Passenger hosting configuration alongside Render`.
