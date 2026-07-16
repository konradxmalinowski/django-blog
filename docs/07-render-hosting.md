# Hosting na Render.com - krok po kroku

Render oferuje darmowy hosting dla aplikacji webowych i baz PostgreSQL.  
Ograniczenia darmowego planu: serwis usypia po 15 minutach braku ruchu (pierwsze zapytanie po uśpieniu trwa ~30 sekund), PostgreSQL za darmo jest usuwana po 90 dniach nieaktywności.

---

## Wymagania wstępne

- Konto na [render.com](https://render.com) (możesz zalogować się przez GitHub)
- Repozytorium na GitHubie (publiczne lub prywatne)
- Gmail App Password do wysyłki emaili (patrz `docs/01-setup.md`)

---

## Krok 1 - Wygeneruj bezpieczny SECRET_KEY

Na swoim komputerze uruchom:

```bash
python3 -c "import secrets; print(secrets.token_hex(50))"
```

Skopiuj wynik - użyjesz go w kroku 4.

---

## Krok 2 - Utwórz bazę PostgreSQL na Render

1. Zaloguj się na [dashboard.render.com](https://dashboard.render.com)
2. Kliknij **New +** → **PostgreSQL**
3. Wypełnij formularz:
   - **Name**: `devlog-db`
   - **Region**: `Frankfurt (EU Central)` *(lub najbliższy)*
   - **Plan**: `Free`
4. Kliknij **Create Database**
5. Poczekaj ~2 minuty aż baza będzie gotowa (`Available`)
6. Na stronie bazy skopiuj wartość **Internal Database URL** - wygląda tak:
   ```
   postgresql://devlog_user:haslo@dpg-xxxxx-a/devlog_db
   ```
   Zachowaj ją - użyjesz jej w kroku 4.

---

## Krok 3 - Utwórz Web Service

1. Kliknij **New +** → **Web Service**
2. Wybierz **Build and deploy from a Git repository** → **Next**
3. Podłącz konto GitHub jeśli to pierwsza usługa, następnie wybierz repozytorium `PPZAW-blog-app`
4. Kliknij **Connect**
5. Wypełnij formularz:
   - **Name**: `devlog` *(lub inna nazwa - ta stanie się Twoim URL: `devlog.onrender.com`)*
   - **Region**: `Frankfurt (EU Central)`
   - **Branch**: `main`
   - **Runtime**: `Python 3`
   - **Build Command**: `./build.sh`
   - **Start Command**: `gunicorn devlog.wsgi:application --bind 0.0.0.0:$PORT --workers 2 --timeout 120`
   - **Plan**: `Free`
6. **Nie klikaj jeszcze Deploy** - najpierw dodaj zmienne środowiskowe (Krok 4)

---

## Krok 4 - Dodaj zmienne środowiskowe

W sekcji **Environment** formularza Web Service (lub po utworzeniu: Settings → Environment) dodaj wszystkie poniższe zmienne:

| Klucz | Wartość |
|-------|---------|
| `DJANGO_SETTINGS_MODULE` | `devlog.settings.production` |
| `SECRET_KEY` | *(wygenerowany w kroku 1)* |
| `DEBUG` | `False` |
| `DATABASE_URL` | *(Internal Database URL z kroku 2)* |
| `ALLOWED_HOSTS` | `.onrender.com` |
| `SITE_URL` | `https://devlog.onrender.com` *(zmień na swój URL)* |
| `SUPERUSER_USERNAME` | `admin` |
| `SUPERUSER_EMAIL` | twój email |
| `SUPERUSER_PASSWORD` | silne hasło do panelu admin |
| `EMAIL_BACKEND` | `django.core.mail.backends.smtp.EmailBackend` |
| `EMAIL_HOST` | `smtp.gmail.com` |
| `EMAIL_PORT` | `587` |
| `EMAIL_USE_TLS` | `True` |
| `EMAIL_HOST_USER` | twój Gmail |
| `EMAIL_HOST_PASSWORD` | Gmail App Password (16 znaków) |
| `DEFAULT_FROM_EMAIL` | `DevLog <twoj@gmail.com>` |

> **Wskazówka**: jeśli nie chcesz teraz konfigurować emaila, ustaw `EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend` - emaile będą tylko logowane, nie wysyłane.

---

## Krok 5 - Deploy

1. Kliknij **Create Web Service** (lub **Manual Deploy** jeśli już utworzyłeś)
2. Render uruchomi `build.sh` - możesz śledzić logi w czasie rzeczywistym w zakładce **Logs**
3. `build.sh` wykona kolejno:
   - `pip install -r requirements/production.txt`
   - `python manage.py collectstatic --no-input`
   - `python manage.py migrate` *(tworzy tabele + superusera + przykładowe posty)*
4. Po sukcesie serwis dostanie status **Live** i URL `https://devlog.onrender.com`

**Spodziewany czas pierwszego deployu**: 3–6 minut.

---

## Krok 6 - Sprawdź działanie

1. Otwórz `https://twoja-nazwa.onrender.com` - powinna pojawić się strona główna bloga
2. Otwórz `https://twoja-nazwa.onrender.com/admin` i zaloguj się danymi z `SUPERUSER_*`
3. Sprawdź `/api/posts/` - powinny pojawić się posty w formacie JSON
4. Sprawdź `/sitemap.xml` i `/robots.txt`

---

## Krok 7 - Zaktualizuj SITE_URL

Po poznaniu dokładnego URL swojego serwisu (np. `devlog-abc123.onrender.com`):

1. W Render dashboard → twój serwis → **Environment**
2. Zmień `SITE_URL` na `https://devlog-abc123.onrender.com`
3. Kliknij **Save Changes** - Render automatycznie zrobi redeploy

---

## Alternatywna metoda - Render Blueprint (render.yaml)

Plik `render.yaml` w repozytorium definiuje całą infrastrukturę. Możesz użyć go zamiast kroków 2-3:

1. W dashboardzie kliknij **New +** → **Blueprint**
2. Wybierz repozytorium
3. Render automatycznie wykryje `render.yaml` i zaproponuje utworzenie bazy + serwisu razem
4. Uzupełnij brakujące zmienne (te oznaczone jako wymagające ręcznego ustawienia)
5. Kliknij **Apply**

> **Uwaga**: `render.yaml` nie zawiera sekretów (`EMAIL_HOST_PASSWORD`, `SUPERUSER_PASSWORD` itp.) - musisz je dodać ręcznie w dashboardzie.

---

## Aktualizacja aplikacji

Każdy `git push` do brancha `main` automatycznie wywołuje nowy deploy na Render.

Aby zatrzymać auto-deploy: Settings → **Auto-Deploy** → wyłącz.  
Ręczny deploy: zakładka **Manual Deploy** → **Deploy latest commit**.

---

## Ważne ograniczenia darmowego planu

| Kwestia | Opis |
|---------|------|
| **Uśpienie serwisu** | Po 15 min bez ruchu serwis usypia; pierwsze żądanie po uśpieniu trwa ~30s |
| **Media (zdjęcia)** | Render free ma efemeryczny filesystem - uploadowane pliki (cover images, avatary) **NIE są persystowane** po restarcie/deployu. Dla produkcji skonfiguruj Cloudinary lub AWS S3. |
| **PostgreSQL TTL** | Darmowa baza jest usuwana po **90 dniach** nieaktywności - rób regularne backupy |
| **RAM** | 512 MB - wystarczy dla małego bloga |
| **CPU** | Shared - możliwe spowolnienia pod obciążeniem |

---

## Backupy bazy danych

Render nie backupuje automatycznie darmowej bazy. Rób backupy ręcznie:

```bash
# Pobierz External Database URL z dashboardu Render (sekcja bazy danych)
pg_dump "postgresql://user:pass@host/db" > backup_$(date +%Y%m%d).sql
```

Lub skonfiguruj cron job na swoim komputerze z `pg_dump` + upload do Google Drive.

---

## Rozwiązywanie problemów

**Build się nie kończy / błąd w logach:**
- Sprawdź czy wszystkie zmienne środowiskowe są ustawione
- Sprawdź logi w zakładce **Logs** w dashboardzie

**`DisallowedHost` error:**
- Upewnij się że `ALLOWED_HOSTS=.onrender.com` jest ustawione

**Strona zwraca 500:**
- Sprawdź logi Render - błędy Django są tam widoczne
- Tymczasowo możesz ustawić `DEBUG=True` żeby zobaczyć szczegóły, ale koniecznie przywróć `False`

**Email nie działa:**
- Upewnij się że Gmail ma włączone 2FA i App Password jest poprawne
- Sprawdź czy `EMAIL_USE_TLS=True`

**Zdjęcia znikają po restarcie:**
- To normalne na free tier (efemeryczny filesystem)
- Skonfiguruj Cloudinary: dodaj `django-cloudinary-storage` i ustaw `CLOUDINARY_URL`
