# notion-apple-sync

Notion-Datenbank → ICS-Subscription-Feed für Apple Calendar (oder andere ICS-Clients).

## Setup

1. Notion Integration anlegen (https://www.notion.so/my-integrations), Token kopieren, Datenbank mit der Integration teilen.
2. Dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Config:
   ```bash
   cp .env.example .env           # NOTION_TOKEN eintragen
   cp config.example.yaml config.yaml
   ```
   Für jeden Kalender einen zufälligen Token erzeugen:
   ```bash
   openssl rand -hex 16
   ```
   `database_id` findest du in der Notion-URL der Datenbank.

## Lokal starten

```bash
uvicorn app.main:app --reload --port 8000
```

Feed öffnen: `http://localhost:8000/cal/<token>.ics`

## Tests

```bash
pytest tests/
```

## Deployment (Docker)

```bash
docker-compose up -d --build
```

Der Service lauscht auf Port 8080. HTTPS über den Reverse Proxy (Traefik / Caddy / nginx) des Hosts.

## In Apple Calendar abonnieren

1. macOS: *Datei → Neues Kalenderabonnement*
2. URL: `https://dein-host.example/cal/<token>.ics`
3. Apple pollt den Feed alle ~15min bis mehrere Stunden (nicht pro Client konfigurierbar).

## Property-Mapping (pro Kalender in `config.yaml`)

| ICS-Feld | Notion-Property |
|----------|-----------------|
| `SUMMARY` | Title (automatisch erkannt) |
| `DTSTART` / `DTEND` | `properties.date` (Date-Property) |
| `DESCRIPTION` | `properties.description` (Rich-Text, optional) |
| `UID` | generiert aus Notion Page-ID — **nie ändern**, sonst verlieren Clients ihren Event-State |

## Caveats

- Apple-Refresh-Intervall ist clientseitig — Änderungen erscheinen nicht sofort.
- Notion Rate Limit ist 3 req/s. Ein In-Memory-Cache (10min TTL) schützt davor.
- All-Day-Range: `DTEND` ist nach RFC 5545 exklusiv — ein 3-Tages-Event von 20.–22. hat `DTEND = 23.`.
