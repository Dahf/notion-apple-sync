# Plan v2: Multi-User Web-Service mit Notion OAuth

## Context

v1 ist ein Single-User-Tool: NOTION_TOKEN in `.env`, Kalender in `config.yaml`, Deployment pro User.

v2 macht daraus einen öffentlichen Self-Service: User kommen auf eine Web-UI, verbinden per Notion-OAuth ihren Workspace, wählen eine Database + Property-Mapping, bekommen eine persönliche ICS-URL. Kein Account-System — die Dashboard-URL ist das Secret.

## User-Entscheidungen (geklärt)

- **Notion Auth**: OAuth (Public Integration bei Notion)
- **Accounts**: Keine — Dashboard-URL `/d/<dashboard_token>` ist die Identität
- **UI**: Jinja2 + HTMX + Tailwind (standalone CLI, kein Node)
- **DB**: SQLite (eine Datei im Docker-Volume)

## User Flow

```
Landing (/)
  └─ [Connect Notion] → Notion OAuth
                          └─ Callback (/oauth/callback)
                               └─ DB: Connection anlegen, dashboard_token erzeugen
                                    └─ Redirect → /d/<dashboard_token>

Dashboard (/d/<dashboard_token>)
  ├─ Liste der angelegten Kalender (mit ICS-URL zum Kopieren)
  ├─ [+ Kalender hinzufügen]
  │     ├─ Notion-DBs vom User laden (HTMX-Partial)
  │     ├─ DB auswählen → Properties laden
  │     ├─ Date-Property wählen (+ optional Description)
  │     ├─ Kalendername vergeben
  │     └─ Submit → DB: Calendar anlegen → ICS-URL anzeigen
  ├─ [Kalender löschen]
  └─ [Notion trennen] → löscht Connection + alle zugehörigen Calendars

ICS (/cal/<subscription_token>.ics)
  └─ wie v1: Notion-Query → ICS-Body, mit 10min Cache
```

## Datenmodell (SQLite)

```python
class Connection:
    id: int (pk)
    dashboard_token: str (unique, secrets.token_urlsafe(32))
    notion_access_token_enc: bytes  # Fernet-verschlüsselt
    workspace_name: str
    workspace_id: str
    bot_id: str
    created_at: datetime

class Calendar:
    id: int (pk)
    connection_id: int (fk → Connection)
    subscription_token: str (unique, secrets.token_urlsafe(32))
    name: str
    database_id: str
    date_property: str
    description_property: str | None
    created_at: datetime
```

## Kritische Design-Entscheidungen

### 1. Notion OAuth

**Setup (einmalig, manuell)**:
- https://www.notion.so/my-integrations → *New integration* → Type: **Public**
- Redirect URI eintragen: `https://<host>/oauth/callback`
- `NOTION_OAUTH_CLIENT_ID` + `NOTION_OAUTH_CLIENT_SECRET` in `.env`

**Flow**:
1. `/oauth/start` → generiert `state` (CSRF), speichert in signed Cookie, redirectet zu:
   ```
   https://api.notion.com/v1/oauth/authorize
     ?client_id=...&response_type=code&owner=user&redirect_uri=...&state=...
   ```
2. `/oauth/callback?code=...&state=...` → verifiziert state → POST zu `https://api.notion.com/v1/oauth/token` mit HTTP-Basic-Auth `(client_id:client_secret)` und JSON-Body `{grant_type, code, redirect_uri}` → bekommt `{access_token, workspace_id, workspace_name, bot_id}` → DB insert → Redirect auf Dashboard

**Wichtig**: Notion OAuth gibt pro Authorization **einen** Token, der Zugriff auf genau die Pages hat, die der User im OAuth-Dialog ausgewählt hat. Bei neuen Pages muss der User den OAuth-Flow erneut durchlaufen (Notion zeigt dann denselben Dialog mit Zusatzauswahl).

### 2. Verschlüsselung der Notion-Tokens

SQLite-Datei könnte bei Backup/Leak offenliegen. Deshalb:

- `FERNET_KEY` in `.env` (einmalig mit `Fernet.generate_key()` generiert)
- `notion_access_token` wird mit Fernet verschlüsselt, bevor es in die DB geht
- Entschlüsselt nur in-Memory, nie geloggt
- Key-Rotation wäre machbar (neuer Key, alle Records re-encrypten), aber out-of-scope für MVP

### 3. Dashboard-URL als Identität

- `dashboard_token` = 32 bytes urlsafe = ~43 Chars → nicht brute-forcebar
- User wird gewarnt: **"Bookmark diese URL — ohne sie kein Zugriff mehr auf deine Kalender. Wir können sie nicht wiederherstellen."**
- Kein Recovery-Flow im MVP (würde Email voraussetzen)

### 4. ICS-Route (bleibt öffentlich)

- `GET /cal/<subscription_token>.ics` — wie v1
- Lookup: `SELECT * FROM calendars WHERE subscription_token = ?`
- Bei Treffer: Connection laden, Notion-Token entschlüsseln, Query laufen lassen, ICS bauen
- 10min TTL-Cache pro subscription_token (wie v1, unverändert)
- 404 bei unbekanntem Token (konstante Timing-Unterschiede sind unkritisch, Token ist 256-bit-Random)

### 5. Sicherheit

- OAuth `state` Parameter (CSRF auf Callback)
- Alle state-ändernden Requests auf Dashboard-Routen: POST + HTMX setzt standardmäßig `HX-Request` Header → simple CSRF-Barriere (plus Same-Origin-Policy bei realem Browser-Setup)
- `dashboard_token` ist in der URL → Warnung an User, keine Browser-Screenshots/History zu teilen
- Kein User-Input in Notion-Queries außer `database_id` (der vom User kommt, aber immer mit seinem eigenen Workspace-Token genutzt wird) → keine SSRF/Injection-Fläche
- HTTPS-only (Set-Cookie `Secure`, HSTS wird vom Reverse Proxy gesetzt)
- Rate Limit: `slowapi` Middleware auf `/oauth/callback` (max 10/min/IP), auf `/cal/*` (max 60/min/IP)

### 6. Caching-Strategie

Zwei Caches:
- **ICS-Cache** (wie v1): key = `subscription_token`, TTL 10min, value = ICS-bytes
- **Database-Liste-Cache** (neu, für UI): key = `connection_id`, TTL 60s, value = List[{id, title, properties}] — damit HTMX-Requests beim Dropdown-Öffnen nicht jedes Mal Notion hämmern

### 7. Migration von v1

v1 war Greenfield und ist frisch. Keine echten User. → Harte Ablösung:
- `config.yaml` / `config.example.yaml` löschen
- `app/config.py` komplett neu (Pydantic-Settings für ENV-Vars, kein YAML mehr)
- `app/notion.py` erweitert: OAuth-Funktionen + weiterhin Property-Parsing + DB-Listing
- `app/ics.py` bleibt **unverändert** (reuse!)
- `app/cache.py` bleibt **unverändert** (reuse!)
- `tests/test_ics.py` bleibt größtenteils, `CalendarConfig` wird durch neues DB-Model ersetzt → Test-Fixtures anpassen

## Neue Projektstruktur

```
notion-apple-sync/
├── app/
│   ├── __init__.py
│   ├── main.py               # FastAPI app, Router-Mounts, Startup
│   ├── settings.py           # Pydantic-Settings (ENV-basiert)
│   ├── db.py                 # SQLAlchemy-Setup, Models, Session
│   ├── crypto.py             # Fernet encrypt/decrypt
│   ├── cache.py              # UNCHANGED
│   ├── ics.py                # UNCHANGED (Mapping von DB-Model statt Config)
│   ├── notion.py             # OAuth + DB-Query + Property-Parsing
│   ├── deps.py               # FastAPI-Dependencies (get_db, get_connection)
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── public.py         # / (Landing), /oauth/start, /oauth/callback, /cal/<token>.ics
│   │   └── dashboard.py      # /d/<token>, /d/<token>/calendars (POST/DELETE), HTMX-Partials
│   ├── templates/
│   │   ├── base.html
│   │   ├── landing.html
│   │   ├── dashboard.html
│   │   └── partials/
│   │       ├── calendar_list.html
│   │       ├── db_picker.html
│   │       └── property_picker.html
│   └── static/
│       └── app.css           # Tailwind-Output
├── tests/
│   ├── test_ics.py           # Angepasst
│   ├── test_crypto.py        # Roundtrip
│   ├── test_oauth.py         # State-Handling, Callback (mit HTTP-Mock)
│   └── test_routes.py        # Dashboard-Flows (FastAPI TestClient)
├── migrations/
│   └── 001_init.sql          # Schema (oder Alembic, MVP: plain SQL)
├── scripts/
│   └── build_css.sh          # Tailwind CLI Build
├── Dockerfile                # Multi-Stage: Tailwind-Build + Python-Runtime
├── docker-compose.yml        # Volume für SQLite + Static
├── requirements.txt
├── .env.example
└── README.md
```

## Environment Variables

```
# v2 neu
NOTION_OAUTH_CLIENT_ID=
NOTION_OAUTH_CLIENT_SECRET=
OAUTH_REDIRECT_URI=https://deinhost/oauth/callback
FERNET_KEY=             # Fernet.generate_key()
SESSION_SECRET=         # für signed state-Cookie bei OAuth
BASE_URL=https://deinhost
DATABASE_URL=sqlite:///./data/app.db
CACHE_TTL=600
```

## Tailwind-Setup (ohne Node)

- `tailwindcss-cli` standalone binary in Dockerfile ziehen
- `scripts/build_css.sh` scannt `app/templates/**/*.html` → schreibt `app/static/app.css`
- Multi-Stage-Dockerfile: Stage 1 = CSS-Build, Stage 2 = Runtime

## Tests

Behalten + neu:
- **Behalten**: alle v1-ICS-Tests (ggf. leichte Fixture-Anpassung)
- **Neu `test_crypto.py`**: Fernet roundtrip, Key-Fehler handhaben
- **Neu `test_oauth.py`**: State-Generation + -Verifikation, Callback mit gemocktem HTTP-Response
- **Neu `test_routes.py`**: 
  - Landing 200
  - Dashboard mit invalid token → 404
  - Dashboard mit valid token → eigene Calendar-Liste sichtbar, fremde nicht
  - Calendar anlegen → taucht in Liste auf
  - Calendar löschen → weg
  - `/cal/<sub>.ics` → korrekter Content-Type, ICS-Body

## Verifikation End-to-End

1. `pytest` grün
2. `docker compose up` lokal, echte Notion Public Integration registriert
3. Browser → `/` → "Connect Notion" → OAuth-Dialog → Callback → Dashboard
4. "Kalender hinzufügen" → DB wählen → Date-Property wählen → ICS-URL anzeigen
5. `curl <ICS-URL>` → valide ICS
6. ICS-Validator (https://icalendar.org/validator.html) → keine Fehler
7. URL in Apple Calendar abonnieren → Events erscheinen
8. Event in Notion ändern → Apple Refresh → Änderung da, keine Duplikate
9. Dashboard: zweiten Kalender anlegen → zweite URL → parallel abonnieren
10. "Trennen" → alle ICS-URLs des Users geben 404

## Aufwandsschätzung

| Block | Aufwand |
|-------|---------|
| Settings + SQLite + SQLAlchemy-Models + Migrations | 1h |
| Crypto-Modul (Fernet) + Tests | 30min |
| Notion OAuth (start + callback + token exchange) | 1.5h |
| Notion DB-Listing + Property-Inspection (für UI) | 1h |
| FastAPI-Routes (public + dashboard) | 1.5h |
| Jinja-Templates + HTMX-Partials | 2h |
| Tailwind-Setup + Styling | 1.5h |
| Tests (crypto, oauth, routes) | 1.5h |
| Docker Multi-Stage + compose anpassen | 45min |
| OAuth manuell bei Notion registrieren + E2E-Test | 1h |

**Gesamt ~12h** — ein volles Wochenende, oder zwei Abende pro Block aufgeteilt.

## Nicht im MVP

- Email-basierter Dashboard-URL-Recovery
- Kalender-Ansicht mit Event-Preview in der UI
- Multi-Property-Support (mehrere Date-Properties pro DB → mehrere Events pro Page)
- Recurring Events aus Notion (Notion hat kein natives Recurrence-Feature)
- Reminders/Alarms (müsste man pro Kalender konfigurieren können)
- Admin-Panel / User-Management
- Postgres-Migration
- Rate-Limiting pro Connection (aktuell nur pro IP)

Das sind alles denkbare v3-Themen.
