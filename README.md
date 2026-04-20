# notion-apple-sync

Self-Service-Webdienst: Notion-Datenbank → ICS-Subscription-Feed für Apple Calendar (oder andere ICS-Clients). Nutzer loggen sich per Magic-Link ein, verbinden ihren Notion-Workspace per OAuth, wählen Database + Property-Mapping, bekommen eine persönliche ICS-URL.

## Stack

- **Backend**: FastAPI + SQLAlchemy (SQLite) + Jinja2 + HTMX + Tailwind CDN
- **Auth**: Magic Link (Resend) + Starlette Session
- **Notion**: Public OAuth Integration, Access-Tokens verschlüsselt (Fernet)
- **Deployment**: Docker + Traefik (HTTPS/HSTS)

## Einmalige Prep

### 1. Resend
1. Account bei [resend.com](https://resend.com) anlegen (Free Tier reicht)
2. Domain `calendar.silasbeckmann.de` verifizieren — DNS-Records (SPF + DKIM) gemäß Resend-Dashboard setzen
3. API-Key kopieren → `RESEND_API_KEY`

### 2. Notion Public Integration
1. [notion.so/my-integrations](https://www.notion.so/my-integrations) → *New integration* → Type **Public**
2. Redirect URI: `https://calendar.silasbeckmann.de/oauth/callback`
3. Client ID + Client Secret kopieren → `NOTION_OAUTH_CLIENT_ID`, `NOTION_OAUTH_CLIENT_SECRET`
4. Public-Submit für Review auslösen (parallel, Integration funktioniert sofort nach Erstellung)

### 3. Secrets generieren
```bash
# FERNET_KEY
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
# SESSION_SECRET
openssl rand -hex 32
```

### 4. Impressum-Daten
In `.env`:
```
IMPRINT_NAME="Max Mustermann"
IMPRINT_ADDRESS="Straße 1\n12345 Stadt"
IMPRINT_EMAIL=kontakt@silasbeckmann.de
```

## Lokal entwickeln

```bash
python -m venv .venv
.venv/Scripts/pip install -r requirements.txt
cp .env.example .env          # Werte eintragen
.venv/Scripts/uvicorn app.main:app --reload --port 8000
```

Besuch `http://localhost:8000/`.

## Tests

```bash
.venv/Scripts/pytest tests/
```

## Deployment

```bash
docker compose up -d --build
```

Traefik-Labels sind in `docker-compose.yml` konfiguriert. SQLite-Datei liegt im gemounteten Volume `./config/app.db`.

## Routen

| Route | Zweck |
|-------|-------|
| `GET /` | Landing |
| `GET /login`, `POST /auth/request`, `GET /auth/verify` | Magic-Link-Flow |
| `POST /auth/logout` | Logout |
| `GET /oauth/start`, `GET /oauth/callback` | Notion OAuth |
| `POST /oauth/disconnect/{id}` | Notion-Workspace trennen |
| `GET /dashboard` | User-Dashboard (auth-required) |
| `POST /dashboard/calendars` | Neuen Kalender anlegen |
| `POST /dashboard/calendars/{id}/delete` | Kalender löschen |
| `GET /cal/{token}.ics` | **Öffentlicher** ICS-Feed |
| `GET /privacy`, `GET /imprint` | Rechtliches |
| `GET /health` | Healthcheck |

## Sicherheit

- Notion-Tokens Fernet-verschlüsselt in der DB
- Magic Links: nur SHA-256-Hash in DB, single-use, 15min Expiry
- OAuth-State-Parameter in Session (CSRF auf Callback)
- CSRF-Token in Form-Hidden-Fields (Session-basiert)
- Rate Limits: `/auth/request` 10/10min/IP, `/cal/*` 60/min/IP
- Session-Cookie: HttpOnly, Secure (bei HTTPS), SameSite=Lax
- Traefik: HSTS, HTTPS-Redirect, Security-Header bereits gesetzt

## Datenmodell

```
User (email)
  └─ Connection (notion_access_token_enc, workspace_name)
       └─ Calendar (subscription_token, database_id, date_property, description_property)
```

## Caveats

- Apple-Refresh-Intervall ist clientseitig (15min–Stunden)
- Notion Rate Limit 3 req/s — In-Memory-Cache (10min TTL) schützt
- All-Day-Range: `DTEND` nach RFC 5545 exklusiv
- Kein Account-Recovery außerhalb Magic Link — Email-Zugriff zwingend nötig
