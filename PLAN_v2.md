# Plan v2: Multi-User Web-Service mit Notion OAuth + Magic-Link-Login

## Context

v1 ist ein Single-User-Tool: NOTION_TOKEN in `.env`, Kalender in `config.yaml`, Deployment pro User. Läuft bereits über Traefik auf `calendar.silasbeckmann.de` mit HTTPS + HSTS.

v2 macht daraus einen öffentlichen Self-Service: User registrieren sich per Email (Magic Link), verbinden ihren Notion-Workspace via OAuth, wählen eine Database + Property-Mapping, bekommen eine persönliche ICS-URL. Ziel: auch für andere Nutzer öffnen, nicht nur Eigenbedarf.

## User-Entscheidungen (geklärt)

- **Login**: Magic Link per Email (kein Passwort)
- **Notion Auth**: OAuth (Public Integration bei Notion)
- **UI**: Jinja2 + HTMX + Tailwind (standalone CLI, kein Node)
- **DB**: SQLite (eine Datei im Docker-Volume, bereits gemountet unter `/app/config`)
- **Email-Provider**: **Resend** (einfache HTTP-API, großzügiger Free Tier, macht SPF/DKIM). SMTP wäre trivial als Alternative (5 Zeilen Swap), falls du lieber deinen eigenen Mailserver nutzt.
- **Reverse Proxy**: Traefik (bereits konfiguriert)

## User Flow

```
Landing (/)
  └─ [Login mit Email]
       └─ POST /auth/request (Email-Input)
            └─ MagicLink in DB anlegen, Mail versenden
                 └─ User klickt Link in Mail
                      └─ GET /auth/verify?token=...
                           └─ User anlegen wenn neu, Session-Cookie setzen
                                └─ Redirect → /dashboard

Dashboard (/dashboard)   [auth-required]
  ├─ (Falls noch keine Notion-Connection): [Connect Notion] → OAuth
  │     └─ Callback → Connection in DB speichern, User zuordnen
  ├─ Liste der Kalender (mit ICS-URL zum Kopieren)
  ├─ [+ Kalender hinzufügen]
  │     ├─ Notion-DBs laden (HTMX-Partial)
  │     ├─ DB auswählen → Properties laden
  │     ├─ Date-Property wählen (+ optional Description)
  │     ├─ Kalendername
  │     └─ Submit → Calendar in DB, ICS-URL anzeigen
  ├─ [Kalender löschen]
  ├─ [Notion-Workspace trennen] → löscht Connection + alle Calendars
  └─ [Logout] → Session-Cookie löschen

ICS (/cal/<subscription_token>.ics)   [public, token-based]
  └─ wie v1: Notion-Query → ICS-Body, 10min Cache
```

## Datenmodell (SQLite / SQLAlchemy)

```python
class User:
    id: int (pk)
    email: str (unique, lowercased)
    created_at: datetime
    last_login_at: datetime | None

class MagicLink:
    id: int (pk)
    email: str (lowercased)            # user_id erst bei Verify gesetzt
    token_hash: str (unique, sha256 hex)  # nur Hash gespeichert
    expires_at: datetime               # now + 15min
    used_at: datetime | None
    created_at: datetime

class Connection:
    id: int (pk)
    user_id: int (fk → User, cascade delete)
    notion_access_token_enc: bytes     # Fernet-verschlüsselt
    workspace_name: str
    workspace_id: str
    workspace_icon: str | None
    bot_id: str
    created_at: datetime
    # Ein User kann theoretisch mehrere Workspaces verbinden → keine Unique-Constraint

class Calendar:
    id: int (pk)
    connection_id: int (fk → Connection, cascade delete)
    subscription_token: str (unique, secrets.token_urlsafe(32))
    name: str
    database_id: str
    date_property: str
    description_property: str | None
    created_at: datetime
```

## Kritische Design-Entscheidungen

### 1. Magic-Link-Login

**Flow**:
1. `GET /login` → Template mit Email-Input
2. `POST /auth/request` mit `{email}` → 
   - Email auf `lower().strip()` normalisieren
   - Rate-Limit prüfen (`slowapi`, 3 Requests/10min/Email **und** pro IP)
   - `raw_token = secrets.token_urlsafe(32)`
   - `token_hash = sha256(raw_token)` → in DB speichern (Raw-Token verlässt DB nicht)
   - Resend-API: Mail an `email` mit Link `https://calendar.silasbeckmann.de/auth/verify?token=<raw_token>`
   - Response: immer `"Wenn die Adresse registriert oder neu ist, findest du den Link in deinem Postfach"` (kein Email-Enumeration-Leak)
3. `GET /auth/verify?token=<raw>` → 
   - `sha256(raw)` in DB suchen
   - Prüfen: nicht expired, `used_at IS NULL`
   - `used_at = now()` setzen
   - User per Email finden oder anlegen
   - `last_login_at` updaten
   - Session-Cookie setzen (`user_id`, signed, `HttpOnly`, `Secure`, `SameSite=Lax`, 30 Tage)
   - Redirect → `/dashboard`
4. `POST /auth/logout` → Cookie löschen, Redirect → `/`

**Security**:
- Nur Hash gespeichert → DB-Leak gibt Angreifer keine gültigen Tokens
- Links sind single-use (`used_at`)
- 15min Expiry
- Same-Device-Check bewusst **nicht** (User öffnet Mail oft auf Phone, will im Desktop-Browser einloggen)

### 2. Session-Management

Starlette `SessionMiddleware` mit `SESSION_SECRET` (32 bytes), signed Cookie, kein Server-Side-Store nötig. Inhalt: `{"user_id": int}`. Rotation bei Logout durch Clear. Cookie-Lifetime 30 Tage Sliding Expiration.

FastAPI-Dependency `get_current_user(request) -> User` → `HTTPException(401) → redirect /login` für Dashboard-Routes.

### 3. Email-Versand (Resend)

- Signup bei resend.com (free), Domain `silasbeckmann.de` verifizieren (DNS: SPF, DKIM, optional DMARC)
- API-Key in ENV
- `httpx` client, POST `https://api.resend.com/emails`:
  ```json
  {
    "from": "Notion Calendar <noreply@calendar.silasbeckmann.de>",
    "to": "user@example.com",
    "subject": "Dein Login-Link",
    "html": "<a href='https://.../auth/verify?token=...'>Einloggen</a> (15 Min gültig)"
  }
  ```
- Fehler beim Mail-Versand → generische 500-Seite, detailliert loggen, Link **nicht** im UI anzeigen
- Fallback-Provider: SMTP via `aiosmtplib` (Modul-Tausch wäre ~20 Zeilen)

### 4. Notion OAuth

Identisch zum vorigen Plan:
- **Setup**: `notion.so/my-integrations` → Public Integration → Redirect URI `https://calendar.silasbeckmann.de/oauth/callback`
- ENV: `NOTION_OAUTH_CLIENT_ID`, `NOTION_OAUTH_CLIENT_SECRET`
- **Flow**:
  1. `/oauth/start` (auth-required) → generiert `state`, schreibt in Session, redirectet zu `https://api.notion.com/v1/oauth/authorize?...&state=...&owner=user`
  2. `/oauth/callback?code=...&state=...` (auth-required) → state prüfen → POST zu `https://api.notion.com/v1/oauth/token` mit Basic-Auth → Token encrypten → Connection anlegen, `user_id` = `session.user_id` → Redirect → `/dashboard`

### 5. Verschlüsselung

- `FERNET_KEY` in ENV (`Fernet.generate_key()`, base64)
- Nur `notion_access_token` verschlüsselt (höchster Wert bei DB-Leak)
- Email-Adressen bleiben Klartext (nötig für Lookup, auch sensibel aber Recovery sonst unmöglich)
- User-Warnung in Privacy-Text: "Wir speichern deine Notion-Tokens verschlüsselt. Bei Kompromittierung unserer Server können Angreifer ohne Key nichts damit anfangen."

### 6. ICS-Route

Unverändert zu v1:
- `GET /cal/<subscription_token>.ics` — öffentlich, kein Auth
- Lookup → Connection → decrypt token → Notion query → ICS
- 10min Cache pro Token (bestehender `cache.py` wiederverwendet)

### 7. Sicherheit (Gesamtpaket)

- Traefik setzt HSTS, HTTPS-Redirect, CT-Header, XSS-Filter (siehe compose-Labels) ✓
- OAuth `state` in Session (CSRF)
- Magic-Link: single-use, 15min, nur Hash in DB, Rate-Limit
- Session-Cookie: `HttpOnly`, `Secure`, `SameSite=Lax`
- HTMX-Requests auf Dashboard haben `HX-Request` Header → CSRF-Barriere für AJAX (Form-Posts brauchen zusätzlich signed Token in Hidden-Field — SessionMiddleware kann das liefern)
- Rate-Limits:
  - `/auth/request`: 3/10min/Email **und** 10/10min/IP
  - `/oauth/callback`: 10/min/IP
  - `/cal/*`: 60/min/IP
- Secrets niemals loggen (custom log filter, oder einfach `repr` von Models ohne sensitive fields)
- Privacy-/Impressum-Seite (für öffentlichen Betrieb in DE rechtlich nötig)

### 8. Caching

Zwei Caches (bestehender `cache.py` + neuer für UI):
- **ICS-Cache**: key = `subscription_token`, TTL 10min, value = ICS-bytes (wie v1)
- **Notion-DB-Liste-Cache**: key = `connection_id`, TTL 60s, value = List[DB-Metadata] — entlastet Notion beim HTMX-Dropdown

### 9. Migration von v1

v1 läuft als persönliche Instanz. Die `config.yaml` mit deinem echten Kalender kann in einem Seed-Skript übernommen werden — aber sauberer: einmal manuell neu einloggen, OAuth machen, Kalender einrichten. Dauert 2min.

- Alte Dateien: `config.py` (YAML-Loader) wird ersetzt durch neuen `settings.py` + DB-Models. `config.example.yaml` kann weg.
- `app/ics.py` bleibt **unverändert** (reuse)
- `app/cache.py` bleibt **unverändert** (reuse)
- `app/notion.py` erweitert (OAuth-Funktionen + DB-Listing) — Property-Parsing bleibt
- Docker-Volume-Mount `./config:/app/config` bleibt, beherbergt jetzt `app.db` + Fernet-Key-File

### 10. Traefik-Setup

Labels sind schon gesetzt — bleiben im Wesentlichen. Einzige Änderung: keine zusätzliche Route, alles läuft unter derselben Domain. Bei Multi-User-Betrieb evtl. später noch:
- `rate-limit` Middleware bei Traefik als zweite Verteidigungslinie
- `forwardAuth` nicht nötig (Auth passiert in-app)

## Neue Projektstruktur

```
notion-apple-sync/
├── app/
│   ├── __init__.py
│   ├── main.py               # FastAPI app, Router-Mounts, Middleware
│   ├── settings.py           # Pydantic-Settings (ENV)
│   ├── db.py                 # SQLAlchemy engine, session, Base
│   ├── models.py             # User, MagicLink, Connection, Calendar
│   ├── crypto.py             # Fernet encrypt/decrypt
│   ├── mailer.py             # Resend-Client
│   ├── auth.py               # Magic-Link-Logik, Session-Helpers, get_current_user
│   ├── cache.py              # UNCHANGED
│   ├── ics.py                # UNCHANGED (Input: Calendar-Model statt Config)
│   ├── notion.py             # OAuth + DB-Query + Property-Parsing
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── public.py         # /, /login, /auth/request, /auth/verify, /cal/<token>.ics, /privacy, /imprint
│   │   ├── oauth.py          # /oauth/start, /oauth/callback, /oauth/disconnect
│   │   └── dashboard.py      # /dashboard, /dashboard/calendars (POST/DELETE), HTMX-Partials, /auth/logout
│   ├── templates/
│   │   ├── base.html         # Layout mit Nav + Flash-Messages
│   │   ├── landing.html
│   │   ├── login.html
│   │   ├── login_sent.html   # "Check deine Mails"
│   │   ├── dashboard.html
│   │   ├── privacy.html
│   │   ├── imprint.html
│   │   ├── email/
│   │   │   └── magic_link.html
│   │   └── partials/
│   │       ├── calendar_list.html
│   │       ├── db_picker.html
│   │       └── property_picker.html
│   └── static/
│       └── app.css           # Tailwind-Output
├── tests/
│   ├── test_ics.py           # Fixtures anpassen (Calendar-Model statt Config)
│   ├── test_crypto.py        # Roundtrip
│   ├── test_auth.py          # Magic-Link flow, Expiry, Single-Use, Hashing
│   ├── test_oauth.py         # State, Callback mit httpx Mock
│   └── test_routes.py        # Dashboard-Auth-Gating, CRUD
├── migrations/               # Alembic (lightweight)
│   └── versions/
├── alembic.ini
├── scripts/
│   └── build_css.sh
├── Dockerfile                # Multi-Stage (Tailwind-Build + Python-Runtime); entrypoint.sh bleibt
├── entrypoint.sh             # (vorhanden) — plus Alembic-Upgrade beim Start
├── docker-compose.yml        # Labels bleiben, neue ENV-Vars
├── requirements.txt
├── .env.example
└── README.md
```

## Environment Variables

```
# Notion OAuth
NOTION_OAUTH_CLIENT_ID=
NOTION_OAUTH_CLIENT_SECRET=
OAUTH_REDIRECT_URI=https://calendar.silasbeckmann.de/oauth/callback

# Secrets
FERNET_KEY=                    # Fernet.generate_key()
SESSION_SECRET=                # 32 bytes urlsafe

# Email (Resend)
RESEND_API_KEY=
MAIL_FROM=Notion Calendar <noreply@calendar.silasbeckmann.de>

# Allgemein
BASE_URL=https://calendar.silasbeckmann.de
DATABASE_URL=sqlite:///./config/app.db
CACHE_TTL=600
```

## Tailwind-Setup (ohne Node)

- Standalone `tailwindcss` Binary in Dockerfile-Builder-Stage
- `scripts/build_css.sh` scannt `app/templates/**/*.html` → schreibt `app/static/app.css`
- Multi-Stage Dockerfile: Stage 1 = CSS-Build, Stage 2 = Runtime (basiert auf dem bereits angepassten Dockerfile mit `gosu`+`entrypoint.sh`)

## Tests

- **test_ics.py** (behalten, Fixtures: Calendar-Model mit subscription_token statt CalendarConfig)
- **test_crypto.py** (neu): Fernet roundtrip, fehlender Key → klare Exception
- **test_auth.py** (neu):
  - request → MagicLink in DB, Hash passt, Raw-Token nur in Mail
  - verify mit gültigem Token → Session-Cookie gesetzt, `used_at` gesetzt, User angelegt
  - verify zweimal mit selbem Token → 400
  - verify nach Expiry → 400
  - Rate-Limit auf `/auth/request`
- **test_oauth.py** (neu): State-Handling, Callback mit gemocktem Notion-Response
- **test_routes.py** (neu):
  - `/dashboard` ohne Session → 302 `/login`
  - Calendar-CRUD happy path
  - User A sieht keine Calendars von User B
  - ICS-Route mit fremdem Token funktioniert (public), mit invalid → 404

## Verifikation End-to-End

1. `pytest` grün
2. Resend-Domain-Setup: SPF + DKIM-DNS-Records, Verification grün
3. Notion Public Integration registriert, Redirect URI produktiv
4. `docker compose up -d --build` → Traefik-Route live
5. Browser → `https://calendar.silasbeckmann.de/` → "Login" → Email eintragen
6. Mail kommt an (in Dev: Resend-Dashboard zeigt Versand)
7. Link klicken → Dashboard sichtbar
8. "Connect Notion" → OAuth-Flow → zurück auf Dashboard mit Workspace-Name
9. "Kalender hinzufügen" → DB wählen → Date-Property → Submit → ICS-URL
10. `curl <ICS-URL>` → valides ICS
11. ICS-Validator → keine Fehler
12. In Apple Calendar abonnieren → Events sichtbar
13. Notion-Event ändern → nach Refresh Update in Apple, keine Duplikate
14. Logout → Dashboard nicht mehr erreichbar, ICS-URL aber weiterhin aktiv (by design)
15. Neuen User mit anderer Email anlegen → sieht eigenes Dashboard, keine Calendars des ersten Users

## Aufwandsschätzung

| Block | Aufwand |
|-------|---------|
| Settings + SQLite + SQLAlchemy + Alembic-Setup | 1.5h |
| User + MagicLink-Models + Migrations | 30min |
| Crypto-Modul | 30min |
| Mailer (Resend) + Template | 45min |
| Auth-Routes (`/login`, request, verify, logout) + Session-Middleware | 1.5h |
| Notion OAuth (start + callback + disconnect) | 1.5h |
| Notion DB-Listing + Property-Inspection | 1h |
| Dashboard-Routes + Calendar-CRUD (HTMX) | 2h |
| Templates (landing, login, dashboard, email, privacy, imprint) | 2.5h |
| Tailwind-Setup + Styling | 1.5h |
| Tests (crypto, auth, oauth, routes) | 2h |
| Docker Multi-Stage + Alembic-Autorun im entrypoint | 45min |
| Resend-Domain-Setup (DNS + Verification) | 30min |
| Notion-OAuth manuell registrieren + E2E-Durchlauf | 1h |
| Privacy/Imprint-Texte | 30min |

**Gesamt ~18h** — realistisch ein Wochenende, oder 3–4 Abendblöcke.

## Nicht im MVP (v3-Kandidaten)

- Social Login (Google, Apple) — Magic Link reicht
- Team-Accounts / shared Workspaces
- Kalender-Ansicht mit Event-Preview in der UI
- Mehrere Date-Properties pro DB → mehrere Events pro Page
- Recurring Events (Notion hat keine native Recurrence)
- Reminders/Alarms konfigurierbar pro Kalender
- Admin-Panel / User-Liste
- Postgres-Migration
- CAPTCHA auf Login (erst bei Abuse nötig)
- Webhook statt Polling (Notion hat Webhooks inzwischen, könnte Cache ersetzen)

## Finale Entscheidungen

- **Mail-From**: `noreply@calendar.silasbeckmann.de`
- **Impressum**: Ja, wird implementiert (Inhalt als Jinja-Template mit Platzhaltern, die du ausfüllst)
- **Notion Public Integration**: Wird als Public registriert. Während Review-Phase läuft die Integration bereits funktional (Notion erlaubt Nutzung vor Approval, nur Listing im Integration-Gallery ist blockiert)

## Manuelle Prep-Schritte (parallel zum Coden durch dich)

1. **Resend-Account** erstellen → Domain `calendar.silasbeckmann.de` verifizieren (DNS: SPF + DKIM hinzufügen, Resend zeigt die Records) → API-Key kopieren
2. **Notion Public Integration** unter [notion.so/my-integrations](https://www.notion.so/my-integrations) erstellen → Type *Public* → Redirect URI `https://calendar.silasbeckmann.de/oauth/callback` → Client-ID + Client-Secret kopieren → Public-Submit für Review (läuft parallel)
3. **Impressum-Daten** bereitstellen: vollständiger Name, postalische Adresse, Kontakt-Email. Ohne diese Pflichtangaben ist der Dienst in DE nicht legal öffentlich betreibbar
4. **Privacy-Text**: Grob-Entwurf kommt im Template — du musst ihn nochmal selbst durchgehen (was gespeichert wird: Email, Notion-Workspace-Name, verschlüsselter Token, IP temporär für Rate-Limits, keine Tracking-Cookies)
5. **ENV-Vars generieren**: `FERNET_KEY` via `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`, `SESSION_SECRET` via `openssl rand -hex 32`
