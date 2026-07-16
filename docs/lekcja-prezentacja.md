# Prezentacja aplikacji - plan lekcji

Blog **DevLog** - zbudowany w Django. Pokazujesz w przeglądarce, tłumaczysz co się dzieje pod spodem.

---

## 1. Lista postów i stronicowanie

**Pokaż w przeglądarce:** strona główna bloga `/blog/`

- Widać listę postów z tytułem, datą, autorem, tagami i fragmentem treści
- Na dole przyciski „poprzednia / następna strona" - kliknij, pokaż zmianę URL (`?page=2`)

**Wyjaśnij jak to działa:**
- Django pobiera z bazy tylko opublikowane posty (`status='published'`) - drafty są niewidoczne
- Stronicowanie dzieli wyniki na strony po 3 posty - baza danych zwraca tylko tyle rekordów ile trzeba, nie wszystkie naraz
- URL strony jest bezstanowy - każdy link do `?page=2` działa samodzielnie, można go skopiować i wysłać

---

## 2. Szczegóły posta i przyjazny URL

**Pokaż w przeglądarce:** kliknij dowolny post, zwróć uwagę na URL

- URL wygląda tak: `/blog/2024/05/21/tytul-posta/` - data + slug
- Wróć, wejdź na inny post - inny URL, ta sama struktura

**Wyjaśnij jak to działa:**
- Slug to skrócona wersja tytułu zbudowana ze słów oddzielonych myślnikami, bez spacji i polskich znaków
- Slug jest unikalny per data - dwa posty tego samego dnia nie mogą mieć tego samego sluga
- Taki URL jest czytelny dla człowieka i dla wyszukiwarek (SEO)
- Jeśli podasz nieistniejącą datę lub slug - dostajesz stronę 404, nie wyjątek aplikacji

---

## 3. Tagi i filtrowanie

**Pokaż w przeglądarce:** kliknij dowolny tag pod postem

- URL zmienia się na `/blog/tag/nazwa-tagu/`
- Lista postów zawiera tylko te z tym tagiem
- Nagłówek strony informuje że filtrujemy po tagu

**Wyjaśnij jak to działa:**
- Jeden post może mieć wiele tagów, jeden tag może być na wielu postach - relacja wiele-do-wielu
- Django filtruje posty przez tę relację w jednym zapytaniu SQL
- Stronicowanie działa tak samo jak na głównej liście

---

## 4. Udostępnianie posta przez e-mail

**Pokaż w przeglądarce:** wejdź na post → kliknij „Udostępnij post"

- Wyświetla się formularz: imię, twój e-mail, e-mail odbiorcy, opcjonalny komentarz
- Wypełnij i wyślij - pojawia się komunikat potwierdzający
- Jeśli wpisz nieprawidłowy e-mail - formularz wraca z komunikatem błędu przy polu

**Wyjaśnij jak to działa:**
- Formularz wysyła dane metodą POST - dane nie są widoczne w URL
- Django sprawdza poprawność każdego pola przed wysłaniem (walidacja) - e-mail musi być e-mailem, imię nie może być puste
- Jeśli cokolwiek jest niepoprawne - formularz jest ponownie pokazany z zaznaczonymi błędami, dane nie są tracone
- Jeśli wszystko OK - Django wysyła e-mail przez skonfigurowany serwer SMTP i pokazuje potwierdzenie

---

## 5. System komentarzy

**Pokaż w przeglądarce:** przewiń na dół strony posta

- Widać listę komentarzy z nazwą, datą i treścią
- Pod nimi formularz do dodania nowego komentarza
- Dodaj komentarz - strona odświeża się, pojawia się komunikat „czeka na moderację"
- Komentarz nie jest jeszcze widoczny na liście

**Wyjaśnij jak to działa:**
- Nowy komentarz ma domyślnie `active=False` - czeka na zatwierdzenie przez administratora
- W panelu admin administrator widzi wszystkie komentarze, może je aktywować lub dezaktywować
- Dopiero po ustawieniu `active=True` komentarz pojawia się pod postem
- Zalogowani użytkownicy mają imię i e-mail uzupełnione automatycznie z konta

**Pokaż w przeglądarce:** panel admin → Komentarze - pokaż zatwierdzanie

---

## 6. Podobne posty

**Pokaż w przeglądarce:** sekcja „Podobne posty" na stronie posta

- Widać do 4 postów powiązanych tematycznie
- Im więcej wspólnych tagów - tym wyżej na liście podobnych

**Wyjaśnij jak to działa:**
- Aplikacja patrzy jakie tagi ma bieżący post
- Szuka wszystkich innych postów które mają chociaż jeden z tych tagów
- Liczy ile tagów mają wspólnego z bieżącym postem
- Sortuje malejąco po tej liczbie - najbardziej podobne na górze
- Wszystko to jedno zapytanie do bazy danych, bez pętli w Pythonie

---

## 7. Wyszukiwarka

**Pokaż w przeglądarce:** wpisz coś w pole wyszukiwania

- Wyniki pojawiają się natychmiast po zatwierdzeniu
- Szuka w tytule, treści i opisie posta jednocześnie
- Jeśli brak wyników - informacja „nic nie znaleziono"

**Wyjaśnij jak to działa:**
- Zapytanie z pola wyszukiwania trafia jako parametr GET w URL (`?query=...`)
- Django przeszukuje trzy pola jednocześnie: tytuł, treść, excerpt
- Wyniki są deduplikowane - post nie pojawia się dwa razy jeśli pasuje do więcej niż jednego pola

---

## 8. Panel administracyjny

**Pokaż w przeglądarce:** `/admin/`

- Zaloguj się jako superuser
- Pokaż listę postów - kolumny, filtry po prawej, wyszukiwarka
- Kliknij post - pokaż formularz edycji, slug wypełnia się automatycznie z tytułu
- Zmień status z `draft` na `published` - post pojawia się na blogu
- Pokaż zakładkę Komentarze - zatwierdź jeden komentarz

**Wyjaśnij jak to działa:**
- Panel admin Django generuje się automatycznie na podstawie modeli
- Nie trzeba pisać żadnego HTML ani formularzy - wystarczy zarejestrować model
- Filtrowanie, wyszukiwanie, stronicowanie - wszystko działa od razu

---

## 9. Rejestracja i konto użytkownika

**Pokaż w przeglądarce:** `/accounts/register/`

- Wypełnij formularz rejestracji
- Pojawia się komunikat o wysłaniu e-maila weryfikacyjnego
- Po kliknięciu linku w e-mailu - konto jest aktywne, automatyczne zalogowanie

**Pokaż w przeglądarce:** profil użytkownika, strona autora `/blog/author/<username>/`

- Lista postów danego autora
- Bio, linki do GitHub/strony

**Wyjaśnij jak to działa:**
- Konto bez potwierdzonego e-maila ma `is_active=False` - nie można się zalogować
- Link w e-mailu zawiera unikalny token UUID ważny 24h - jednorazowy
- Każdy użytkownik ma automatycznie tworzony profil (bio, avatar, linki)

---

## 10. Weryfikacja dwuetapowa (2FA)

**Pokaż w przeglądarce:** Ustawienia konta → „Włącz weryfikację dwuetapową"

- Pojawia się kod QR - zeskanuj go aplikacją (Google Authenticator, Authy, Bitwarden)
- Wpisz 6-cyfrowy kod z aplikacji - 2FA jest włączone
- Pojawia się jednorazowo lista 8 kodów zapasowych - pokaż że trzeba je zapisać, bo nie będą pokazane ponownie
- Wyloguj się i zaloguj ponownie - po poprawnym haśle pojawia się dodatkowy ekran z polem na kod

**Wyjaśnij jak to działa:**

- Hasło to coś co znasz - można je ukraść, podsłuchać, wyciągnąć z bazy
- Kod z aplikacji to coś co masz (telefon) - nawet jeśli ktoś zna hasło, bez telefonu się nie zaloguje
- Aplikacja i serwer generują ten sam 6-cyfrowy kod niezależnie od siebie, bez połączenia z internetem - na podstawie wspólnego sekretu i aktualnego czasu
- Kod zmienia się co 30 sekund i jest jednorazowy - przechwycony kod jest bezużyteczny po upływie okna czasowego
- Backup codes - jeśli zgubisz telefon, możesz się zalogować jednym z 8 kodów jednorazowych; każdy kod po użyciu jest unieważniany

**Pokaż w przeglądarce:** spróbuj zalogować się z błędnym kodem TOTP - pojawia się błąd; po 5 błędnych próbach adres IP jest blokowany na godzinę

---

## 11. RSS Feed

**Pokaż w przeglądarce:** `/blog/feed/`

- Przeglądarka pokazuje XML z ostatnimi postami
- Wklej URL do czytnika RSS (np. Feedly) - posty pojawiają się automatycznie

**Wyjaśnij jak to działa:**
- Feed generuje się dynamicznie - zawsze zawiera najnowsze opublikowane posty
- Czytniki RSS mogą sprawdzać ten URL co jakiś czas i informować o nowych postach
- Jest też osobny feed per kategoria: `/blog/feed/category/<slug>/`

---

## 12. REST API

**Pokaż w przeglądarce:** `/api/`

- Klikalna dokumentacja - można przeglądać i testować endpointy bez żadnych narzędzi
- Wejdź na `/api/posts/` - lista postów w formacie JSON
- Pokaż `/api/posts/<slug>/` - szczegóły jednego posta

**Pokaż w przeglądarce lub terminalu:** pobieranie tokenu i chroniony endpoint

```
POST /api/auth/token/  {"username": "...", "password": "..."}
→ {"token": "abc123..."}

GET /api/posts/  Authorization: Token abc123...
```

**Wyjaśnij jak to działa:**
- API zwraca te same dane co strona, ale w formacie JSON zamiast HTML
- Dzięki temu inny program (aplikacja mobilna, skrypt, frontend w React) może korzystać z tych samych danych
- Tworzenie postów i komentarzy przez API wymaga tokenu - bez niego można tylko czytać

---

## Kolejność pokazywania na lekcji

1. Lista postów → stronicowanie
2. Szczegóły posta → URL z datą i slugiem
3. Tagi → kliknij tag, filtrowanie
4. Udostępnianie przez e-mail → formularz, walidacja, wysyłka
5. Komentarze → dodaj, pokaż moderację w admin
6. Podobne posty → wyjaśnij algorytm
7. Wyszukiwarka
8. Panel admin → posty, komentarze, zmiana statusu
9. Rejestracja i konto
10. 2FA - włączanie, QR kod, backup codes, logowanie z kodem
11. RSS Feed
12. API (jeśli zostanie czas)
