# Hosting na CT8 (MyDevil/Small.pl, Passenger) — krok po kroku

CT8 to darmowy hosting współdzielony oparty o ten sam panel co MyDevil/Small.pl (Phusion Passenger). W przeciwieństwie do Render: filesystem jest trwały (SQLite i pliki media przetrwają restart), ale deploy jest ręczny — nie ma automatycznego builda po `git push`.

Ta konfiguracja działa **równolegle** do Render (`docs/07-render-hosting.md`) — nie zastępuje jej.

---

## Wymagania wstępne

- Konto na [ct8.pl](https://ct8.pl) (darmowe) z dostępem SSH
- Domena/subdomena przypisana do konta (np. `twojlogin.ct8.pl` albo własna domena podpięta w panelu)
- Podstawowa znajomość SSH

---

## Krok 1 — Wygeneruj bezpieczny SECRET_KEY

Na swoim komputerze:

```bash
python3 -c "import secrets; print(secrets.token_hex(50))"
```

Zachowaj wynik — użyjesz go w `.env` (krok 5).

---

## Krok 2 — Połącz się przez SSH i utwórz virtualenv

```bash
ssh twojlogin@ct8.pl
python3 -m venv ~/.virtualenvs/devlog
source ~/.virtualenvs/devlog/bin/activate
```

Nazwa środowiska (`devlog`) jest dowolna — zapamiętaj ją, wpiszesz ją w panelu w kroku 7.

---

## Krok 3 — Wgraj kod projektu

Katalog na kod na CT8 to zwykle `~/domains/<domena>/public_python`. Najprościej sklonować repo bezpośrednio tam:

```bash
cd ~/domains/twojlogin.ct8.pl
rmdir public_python   # panel tworzy pusty katalog — usuń go przed git clone
git clone https://github.com/<twoj-user>/PPZAW-blog-app.git public_python
cd public_python
```

---

## Krok 4 — Zainstaluj zależności

W aktywnym virtualenv z kroku 2:

```bash
pip install -r requirements/ct8.txt
```

`requirements/ct8.txt` zawiera tylko to, co potrzebne pod Passenger + SQLite + WhiteNoise — bez `gunicorn` i `psycopg2-binary` (to zależności Render/PostgreSQL, niepotrzebne tutaj).

---

## Krok 5 — Utwórz plik `.env`

CT8 nie ma UI na zmienne środowiskowe jak Render — `python-decouple` czyta je z pliku `.env` w katalogu projektu.

```bash
cp .env.ct8.example .env
nano .env
```

Uzupełnij:
- `SECRET_KEY` — wygenerowany w kroku 1
- `ALLOWED_HOSTS` i `SITE_URL` — Twoja domena/subdomena
- `SUPERUSER_USERNAME` / `SUPERUSER_EMAIL` / `SUPERUSER_PASSWORD` — dane do panelu `/admin`

---

## Krok 6 — Zbierz statyki i uruchom migracje

Nadal w virtualenv, w katalogu projektu:

```bash
export DJANGO_SETTINGS_MODULE=devlog.settings.ct8
python manage.py collectstatic --no-input
python manage.py migrate
```

---

## Krok 7 — Skonfiguruj stronę Python w panelu CT8

W panelu (webapp.ct8.pl lub podobny adres panelu) → **Strony WWW** → **Dodaj stronę** → typ **Python**:

| Pole | Wartość |
|------|---------|
| **Domena** | Twoja domena/subdomena (np. `twojlogin.ct8.pl`) |
| **Plik wykonywalny** | `/usr/home/twojlogin/.virtualenvs/devlog/bin/python` |
| **Środowisko** | `production` |

Panel sam utworzy/uzupełni strefę DNS dla domeny.

---

## Krok 8 — Restart aplikacji

Passenger uruchamia aplikację raz i trzyma ją w pamięci — po każdej zmianie kodu lub `.env` trzeba wymusić restart:

```bash
mkdir -p ~/domains/twojlogin.ct8.pl/public_python/tmp
touch ~/domains/twojlogin.ct8.pl/public_python/tmp/restart.txt
```

---

## Krok 9 — Sprawdź działanie

1. Otwórz `https://twojlogin.ct8.pl` — powinna pojawić się strona główna bloga
2. Otwórz `https://twojlogin.ct8.pl/admin` i zaloguj się danymi z `SUPERUSER_*`
3. Sprawdź `/api/posts/` — posty w formacie JSON
4. Sprawdź `/sitemap.xml` i `/robots.txt`

---

## Aktualizacja aplikacji

Deploy na CT8 jest ręczny:

```bash
ssh twojlogin@ct8.pl
cd ~/domains/twojlogin.ct8.pl/public_python
git pull
source ~/.virtualenvs/devlog/bin/activate
pip install -r requirements/ct8.txt
python manage.py collectstatic --no-input
python manage.py migrate
touch tmp/restart.txt
```

---

## Różnice względem Render

| Kwestia | Render (free) | CT8 |
|---------|---------------|-----|
| Filesystem | Efemeryczny — media znikają po restarcie | Trwały — SQLite i media zostają |
| Deploy | Automatyczny po `git push` | Ręczny (`git pull` + restart) |
| Uśpienie | Po 15 min bez ruchu | Brak |
| Baza danych | PostgreSQL (osobna usługa) | SQLite (plik w projekcie) |
| Serwer aplikacji | gunicorn | Passenger (przez `passenger_wsgi.py`) |

---

## Rozwiązywanie problemów

**Strona zwraca 500:**
- Sprawdź logi błędów Passenger w panelu CT8 (sekcja logów strony WWW)
- Upewnij się, że `.env` istnieje i zawiera `SECRET_KEY`

**`DisallowedHost` error:**
- Sprawdź `ALLOWED_HOSTS` w `.env` — musi pasować dokładnie do domeny z panelu

**Zmiany w kodzie nie widać po `git pull`:**
- Passenger cache'uje aplikację w pamięci — zrób `touch tmp/restart.txt`

**Pliki statyczne (CSS/JS) nie ładują się:**
- Upewnij się, że `collectstatic` zostało uruchomione po ostatnim deployu
- Sprawdź, że `DJANGO_SETTINGS_MODULE=devlog.settings.ct8` jest aktywne przy uruchamianiu `manage.py`

**Błąd przy `pip install psycopg2-binary` lub podobny:**
- Nie powinno się zdarzyć przy `requirements/ct8.txt` — jeśli widzisz ten błąd, sprawdź czy przypadkiem nie zainstalowałeś `requirements/production.txt` (wersja pod Render/PostgreSQL)
