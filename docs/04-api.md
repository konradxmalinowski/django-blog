# REST API

Zbudowane na Django REST Framework. Autoryzacja przez **Token Authentication**.

## Autentykacja

### Uzyskanie tokenu

```bash
curl -X POST http://127.0.0.1:8000/api/auth/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "twoj_user", "password": "twoje_haslo"}'
```

Odpowiedź:
```json
{"token": "9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b"}
```

### Użycie tokenu

```bash
curl http://127.0.0.1:8000/api/posts/ \
  -H "Authorization: Token 9944b09199c62bcf9418ad846dd0e4bbdfc6ee4b"
```

---

## Endpointy

### Posty

#### `GET /api/posts/`

Lista opublikowanych postów.

```json
[
  {
    "id": 1,
    "title": "Tytuł posta",
    "slug": "tytul-posta",
    "author": "admin",
    "category": "Backend",
    "excerpt": "Krótki opis...",
    "publish": "2026-05-23T10:00:00Z",
    "reading_time": 3,
    "tags": ["django", "python"]
  }
]
```

#### `POST /api/posts/` - wymaga tokenu

```json
{
  "title": "Nowy post",
  "slug": "nowy-post",
  "body": "## Treść\n\nMarkdown...",
  "status": "published",
  "category": 1
}
```

#### `GET /api/posts/<slug>/`

Szczegóły jednego posta (pełna treść + `body_html`).

#### `PUT /api/posts/<slug>/` - wymaga tokenu (author lub admin)

#### `DELETE /api/posts/<slug>/` - wymaga tokenu (author lub admin)

---

### Komentarze

#### `GET /api/posts/<slug>/comments/`

Lista aktywnych komentarzy posta.

#### `POST /api/posts/<slug>/comments/`

```json
{
  "name": "Imię",
  "email": "email@example.com",
  "body": "Treść komentarza"
}
```

---

### Tagi i kategorie

#### `GET /api/tags/`

```json
[{"id": 1, "name": "django", "slug": "django"}]
```

#### `GET /api/categories/`

```json
[{"id": 1, "name": "Backend", "slug": "backend", "color": "#7ee787"}]
```

---

## Permissions

| Akcja | Wymagana rola |
|-------|--------------|
| Odczyt postów/komentarzy/tagów | Wszyscy |
| Tworzenie posta | Zalogowany (token) |
| Edycja/usunięcie posta | Autor posta lub admin |
| Dodanie komentarza | Wszyscy |

Klasa uprawnień: `IsAuthorOrReadOnly`.

---

## Przykłady curl

```bash
# Lista postów
curl http://127.0.0.1:8000/api/posts/

# Szczegóły posta
curl http://127.0.0.1:8000/api/posts/moj-post-slug/

# Komentarze posta
curl http://127.0.0.1:8000/api/posts/moj-post-slug/comments/

# Nowy post (auth)
curl -X POST http://127.0.0.1:8000/api/posts/ \
  -H "Authorization: Token <token>" \
  -H "Content-Type: application/json" \
  -d '{"title":"Test","slug":"test","body":"# Treść","status":"published"}'

# Usuń post (auth)
curl -X DELETE http://127.0.0.1:8000/api/posts/test/ \
  -H "Authorization: Token <token>"
```
