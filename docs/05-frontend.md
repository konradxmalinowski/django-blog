# Frontend

## Design system - terminal theme

DevLog używa własnego arkusza CSS (`static/css/terminal.css`) opartego na motywie terminal dark. Cały design system opiera się na zmiennych CSS definiowanych w `:root`.

### Zmienne kolorów (CSS custom properties)

```css
/* Tła */
--bg:             #0d1117   /* tło strony */
--bg-card:        #161b22   /* tło kart/widgetów */
--bg-border:      #1e3d1e   /* obramowania */
--bg-hover:       #1c2b1c   /* hover stanu */
--bg-code:        #060e06   /* tło bloków kodu */

/* Tekst */
--text-primary:   #e0e0e0
--text-secondary: #9e9e9e
--text-muted:     #5a5a5a

/* Akcenty */
--accent-green:   #00ff41   /* komendy, nagłówki, CTA */
--accent-lime:    #39d353   /* alternatywny zielony */
--accent-blue:    #58d68d   /* linki, tagi */
--accent-warn:    #ffd700   /* ostrzeżenia */
--accent-error:   #ff4444   /* błędy */
```

### Tryb jasny (`.light-mode`)

Klasa dodawana/usuwana dynamicznie z `document.body` przez JS. Wszystkie zmienne są nadpisywane:

```css
.light-mode {
  --bg:           #f6f8fa
  --bg-card:      #ffffff
  --accent-green: #1a7f37
  --accent-blue:  #0550ae
  /* ... */
}
```

Preferencja zapisywana w `localStorage` klucz `theme`. Przy braku preferencji: `prefers-color-scheme: dark` → dark, inaczej → light.

### Typografia

```css
--font-mono: 'JetBrains Mono', 'Fira Code', 'Cascadia Code', 'Consolas', monospace
--font-size: 15px
--line-height: 1.75
```

Font ładowany z Google Fonts (`@import` w `base.html`).

### Layout

```css
--navbar-height:    56px
--content-max-width: 1100px
--sidebar-width:    260px
```

Grid: `main-grid` - dwukolumnowy layout (treść + sidebar), przełącza się na jedną kolumnę przy `max-width: 900px`.

---

## Komponenty CSS

### ASCII-box karta

Karty postów i widgety używają pseudoobramowania z box-drawing characters:

```
┌─────────────────────┐
│  zawartość karty    │
└─────────────────────┘
```

Klasy: `.terminal-box`, `.sidebar-widget`, `.post-card`.

### Pseudoprompt breadcrumbs

Nawigacja okruszków w stylu terminala:

```
~/blog/posts$ tytuł-posta
```

Klasa: `.breadcrumb-prompt`.

### ASCII progress bar - czas czytania

Pasek widoczny na stronie szczegółów posta:

```
[████████░░] 4 min
```

Klasa: `.reading-time-bar`.

### Pasek postępu czytania

Poziomy pasek na górze viewport podczas scrollowania artykułu:

```css
#reading-progress { position: fixed; top: 0; left: 0; height: 2px; background: var(--accent-green); }
```

### Status badges

```html
<span class="status-badge status-badge--published">published</span>
<span class="status-badge status-badge--draft">draft</span>
```

### Moderator badge

```html
<span class="moderator-badge">[MOD]</span>
```

### Paginacja z numerami stron

```html
<nav class="pagination" aria-label="Nawigacja stron">
  <div class="pagination-pages">
    <a class="pagination-page" href="?page=1">1</a>
    <span class="pagination-ellipsis">…</span>
    <a class="pagination-page pagination-page--active" aria-current="page">3</a>
  </div>
</nav>
```

### Sidebar newsletter

Widget newslettera z `class="sidebar-newsletter"` - pierwsze miejsce w sidebarze (widoczność bez scrollowania).

### Accessibility

`.sr-only` - klasa dla elementów widocznych tylko dla screen readerów:

```css
.sr-only {
  position: absolute;
  width: 1px; height: 1px;
  overflow: hidden;
  clip: rect(0,0,0,0);
  white-space: nowrap;
}
```

---

## JavaScript - terminal.js

Plik `static/js/terminal.js`, ładowany na końcu `<body>`. Cały kod uruchamiany na `DOMContentLoaded`.

### Funkcje

| Funkcja | Opis |
|---------|------|
| `initReadingProgress()` | Aktualizuje `#reading-progress` szerokość przy scrollu |
| `initMessages()` | Auto-dismiss wiadomości Django (`data-auto-dismiss`) po 4s |
| `initSmoothScroll()` | Smooth scroll dla kotew `a[href^="#"]` |
| `initLazyLoading()` | IntersectionObserver dla `img[data-src]` (lazy load) |
| `initPrefetch()` | Prefetch na hover dla wewnętrznych linków |
| `initExternalLinks()` | Dodaje `rel="noopener noreferrer"` i `target="_blank"` dla zewnętrznych |
| `initThemeToggle()` | Obsługuje `#theme-toggle`, `localStorage`, `.light-mode` |
| `initToc()` | IntersectionObserver dla aktywnego linku w spis treści |

### Generowanie hasła (inline JS)

W szablonach rejestracji i resetowania hasła - inline `<script>` z:

```js
function generatePassword() {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789!@#$%';
  const arr = new Uint32Array(16);
  crypto.getRandomValues(arr);
  return Array.from(arr, n => chars[n % chars.length]).join('');
}
```

Używa `crypto.getRandomValues` (CSPRNG) - nie `Math.random()`.

---

## Responsywność

Breakpointy:

| Szerokość | Zachowanie |
|-----------|-----------|
| > 900px | Dwukolumnowy grid (treść + sidebar) |
| ≤ 900px | Jednokolumnowy, sidebar pod treścią |
| ≤ 600px | Zmniejszone paddingi, navbar hamburger |

---

## Szablony

Wszystkie szablony w `templates/` (nie w apps/).

| Plik | Opis |
|------|------|
| `base.html` | Bazowy layout, navbar, footer, CSS/JS |
| `partials/navbar.html` | Nawigacja, theme toggle, user menu |
| `partials/sidebar.html` | Newsletter, ostatnie posty, tag cloud |
| `partials/pagination.html` | Paginacja z numerami stron |
| `partials/messages.html` | Django messages z auto-dismiss |
| `blog/post_list.html` | Lista postów |
| `blog/post_detail.html` | Szczegół posta, komentarze, ToC, reakcje |
| `blog/author_post_list.html` | Panel autora/moderatora (tabela postów) |
| `accounts/register.html` | Formularz rejestracji + generator hasła |
| `accounts/password_reset_confirm.html` | Reset hasła + generator hasła |
| `accounts/settings.html` | Ustawienia konta, 2FA, zmiana emaila |
