# Funkcje użytkownika

## Blog

### Lista postów

Strona główna (`/`) wyświetla opublikowane posty posortowane od najnowszych. Paginacja: 5 postów na stronę z numerami stron i elipsami.

Filtrowanie:
- Po tagu: `/tag/<slug>/`
- Po kategorii: `/category/<slug>/`
- Po autorze: `/author/<username>/`
- Wyszukiwanie pełnotekstowe: `/search/?q=<query>`

### Szczegół posta

URL: `/<rok>/<mies>/<dzień>/<slug>/`

Elementy strony:
- Pełna treść Markdown (renderowana + sanityzowana bleach)
- Spis treści (automatyczny z nagłówków H2/H3)
- Pasek postępu czytania (u góry viewport)
- Szacowany czas czytania (pasek ASCII)
- Reakcje (lajk) - AJAX, wymaga logowania
- Zakładka (bookmark) - AJAX, wymaga logowania
- Sekcja komentarzy
- Formularz komentarza (wszyscy użytkownicy)

### Komentarze

Formularz: `name`, `email`, `body`.

Walidacja:
- Pola wymagane
- Treść sanityzowana przez `bleach` (whitelist tagów)
- Filtr przekleństw (PL+EN) - odrzuca formularz
- Rate limit: 5 komentarzy/minutę na IP

Po wysłaniu - PRG redirect (zapobiega duplikatom przy odświeżeniu). Komentarz trafia do moderacji (`active=False`) i pojawia się po zatwierdzeniu przez admina.

### Reakcje i zakładki

- **Reakcja** (lajk): przycisk `[♥ N]` - AJAX POST na `/posts/<id>/react/`
- **Zakładka**: przycisk `[⊙ bookmark]` - AJAX POST na `/posts/<id>/bookmark/`
- Lista zakładek: `/bookmarks/` (wymaga logowania)

---

## Konta użytkowników

### Rejestracja

URL: `/accounts/register/`

1. Wypełnij formularz (username, email, hasło)
2. Kliknij "Generuj hasło" dla losowego bezpiecznego hasła (CSPRNG)
3. Po rejestracji - email z linkiem weryfikacyjnym (ważny 24h)
4. Kliknij link → konto aktywowane, automatyczne zalogowanie

### Logowanie

URL: `/accounts/login/`

Po zalogowaniu z włączonym 2FA → przekierowanie na `/accounts/2fa/verify/`.

Ochrona brute-force: 5 nieudanych prób → blokada konta na 1h.

### Profil publiczny

URL: `/accounts/<username>/`

Pokazuje: avatar, bio, linki (GitHub, strona), lista postów użytkownika.

### Ustawienia konta

URL: `/accounts/settings/`

Zakładki:
- Zmiana hasła: `/accounts/settings/password/`
- Zmiana emaila: `/accounts/settings/email/` (wymaga ponownej weryfikacji)
- Ustawienia 2FA: `/accounts/settings/2fa/`

---

## Dwuskładnikowe uwierzytelnienie (2FA)

### Włączanie 2FA

1. Przejdź do `/accounts/settings/2fa/`
2. Zeskanuj QR code w aplikacji (Google Authenticator, Authy, Bitwarden, 1Password)
3. Wpisz 6-cyfrowy kod z aplikacji
4. 2FA włączone - jednorazowo wyświetlane 8 kodów zapasowych

### Logowanie z 2FA

Po wpisaniu hasła → formularz weryfikacji TOTP na `/accounts/2fa/verify/`.

Możliwości:
- 6-cyfrowy kod z aplikacji TOTP
- 10-znakowy kod zapasowy (jednorazowy)

Rate limit: 5 prób/minutę.

### Kody zapasowe

8 jednorazowych kodów (10-znakowe hex, uppercase). Przechowywane jako PBKDF2 hashes.

Generowanie/podgląd: `/accounts/settings/2fa/backup-codes/`
Regeneracja (wymaga aktualnego kodu TOTP): `/accounts/settings/2fa/backup-codes/regenerate/`

Po użyciu kodu zapasowego - oznaczany jako zużyty, nie może być użyty ponownie.

### Wyłączanie 2FA

URL: `/accounts/settings/2fa/disable/`

---

## Newsletter

Widget w górnej części sidebaru na każdej stronie.

### Subskrypcja

1. Wpisz email w sidebar lub na stronie `/newsletter/subscribe/`
2. Otrzymasz email z linkiem potwierdzającym
3. Kliknij link → subskrypcja aktywna

### Powiadomienia

Subskrybenci otrzymują email przy każdym nowym opublikowanym poście (automatycznie przez sygnał Django `post_save`).

### Wypisanie

Link w każdym emailu newslettera: `/newsletter/unsubscribe/<uuid>/`

Rate limit subskrypcji: 5 prób/h na IP.

---

## Panel autora

URL: `/author/posts/` (wymaga logowania)

Tabela wszystkich własnych postów z kolumnami: tytuł, data, status, wyświetlenia, akcje.

### Nowy post

URL: `/author/posts/new/`

Formularz z edytorem Markdown (django-markdownx), tytułem, kategorią, tagami, opisem, obrazem.

### Edycja posta

URL: `/author/posts/<slug>/edit/`

### Usunięcie posta

URL: `/author/posts/<slug>/delete/` - strona potwierdzenia.

---

## Panel moderatora

Moderatorem jest każdy użytkownik z flagą `is_staff` (ustawianą w panelu admin).

Moderator w panelu `/author/posts/`:
- Widzi WSZYSTKIE posty (nie tylko własne)
- Może edytować i usuwać posty innych autorów
- Widoczna flaga `[MOD]` przy nazwie użytkownika

---

## RSS

- `/feed/` - wszystkie opublikowane posty
- `/feed/category/<slug>/` - posty z konkretnej kategorii

Obsługiwane przez wszystkie czytniki RSS (Atom 1.0).

---

## SEO

- Sitemap XML: `/sitemap.xml`
- Robots.txt: `/robots.txt`
- Canonical URL: `<link rel="canonical">` na każdej stronie
- Open Graph meta tags: `og:title`, `og:description`, `og:image`
- Meta description: per post i per kategoria
