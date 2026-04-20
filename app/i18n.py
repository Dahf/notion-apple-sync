from fastapi import Request

SUPPORTED = ("de", "en")
DEFAULT = "de"

TRANSLATIONS: dict[str, dict[str, str]] = {
    "de": {
        # Nav / shared
        "nav.dashboard": "Dashboard",
        "nav.logout": "Logout",
        "nav.login": "Einloggen",
        "nav.lang_label": "Sprache",
        "footer.made_with_care": "Mit Sorgfalt gemacht",
        "footer.imprint": "Impressum",
        "footer.privacy": "Datenschutz",
        "toast.close": "Schließen",
        "modal.confirm_kicker": "— Bitte bestätigen",
        "modal.confirm_title": "Sicher?",
        "modal.confirm_body": "Aktion wirklich ausführen?",
        "modal.cancel": "Abbrechen",
        "modal.confirm": "Bestätigen",

        # Landing
        "landing.kicker": "Ein kleines, sorgfältiges Werkzeug",
        "landing.title_1": "Dein Notion-Kalender,",
        "landing.title_em": "wo immer",
        "landing.title_2": "du ihn brauchst.",
        "landing.lead": "Verbinde eine Notion-Datenbank, wähle Deine Datums-Spalte — und bekomme eine ICS-Abonnement-URL, die Apple Calendar, Google Calendar und jeder andere Kalender-Client versteht.",
        "landing.cta_start": "Loslegen",
        "landing.cta_free": "Kostenlos · kein Passwort",
        "landing.how_kicker": "— Wie es funktioniert",
        "landing.step1_title": "Einloggen",
        "landing.step1_body_1": "E-Mail eintragen. Wir schicken Dir einen Link —",
        "landing.step1_body_em": "ein Klick genügt",
        "landing.step1_body_2": ". Kein Passwort, nie wieder vergessen.",
        "landing.step2_title": "Notion verbinden",
        "landing.step2_body": "Offizielle OAuth-Verbindung. Du bestimmst, welche Datenbanken wir überhaupt zu sehen bekommen.",
        "landing.step3_title": "Abonnieren",
        "landing.step3_body_1": "URL kopieren, in Apple Calendar einfügen.",
        "landing.step3_body_em": "Fertig.",
        "landing.step3_body_2": "Änderungen in Notion erscheinen automatisch.",
        "landing.quote": "„Kalender verdienen Sorgfalt.\u00a0 Dies ist keine Plattform — es ist ein Stück Handwerk, das eine konkrete Aufgabe elegant löst.\"",
        "landing.live_title_1": "Notion-Daten,",
        "landing.live_title_em": "live",
        "landing.live_title_2": "im Kalender.",
        "landing.live_body": "Jede Änderung in Deiner Notion-Datenbank erscheint automatisch in Deinem Kalender. Apple\u00a0Calendar, Google\u00a0Calendar — alles via ICS.",
        "landing.preview_month": "April 2026",
        "weekday.mon": "Mo",
        "weekday.tue": "Di",
        "weekday.wed": "Mi",
        "weekday.thu": "Do",
        "weekday.fri": "Fr",
        "weekday.sat": "Sa",
        "weekday.sun": "So",

        # Dashboard
        "dashboard.kicker": "— Dashboard",
        "dashboard.title_1": "Deine",
        "dashboard.title_em": "Kalender",
        "dashboard.lead": "Verbinde Notion-Workspaces und wähle pro Datenbank, welches Datum exportiert wird.",
        "dashboard.empty_title": "Noch keine Verbindung",
        "dashboard.empty_body": "Verknüpfe Deinen Notion-Workspace via OAuth. Du entscheidest, welche Seiten wir sehen dürfen.",
        "dashboard.connect_notion": "Notion verbinden",
        "dashboard.workspace_label": "Notion Workspace",
        "dashboard.disconnect": "trennen",
        "dashboard.disconnect_confirm": "Wenn Du diesen Workspace trennst, werden alle zugehörigen Kalender-Feeds sofort ungültig. Sicher?",
        "dashboard.disconnect_title": "Workspace trennen",
        "dashboard.disconnect_label": "Ja, trennen",
        "dashboard.no_calendars": "Noch keine Kalender aus diesem Workspace. Füge unten einen hinzu.",
        "dashboard.copy": "kopieren",
        "dashboard.copied": "kopiert ✓",
        "dashboard.edit": "bearbeiten",
        "dashboard.add_calendar": "Kalender hinzufügen",
        "dashboard.loading_databases": "Lade Datenbanken aus Notion …",
        "dashboard.connect_another": "Weiteren Workspace verbinden",

        # Login
        "login.kicker": "— Willkommen zurück",
        "login.title": "Einloggen",
        "login.lead_1": "Wir schicken Dir einen",
        "login.lead_em": "Link",
        "login.lead_2": ". Fünfzehn Minuten gültig.",
        "login.email_label": "E-Mail",
        "login.email_placeholder": "du@beispiel.de",
        "login.submit": "Link senden",
        "login.new_here": "Neu hier? Auch dann — wir legen dein Konto automatisch an.",
        "login.error_invalid": "Link ungültig oder abgelaufen.",

        # Login sent
        "login_sent.title": "Schau in Dein Postfach.",
        "login_sent.body_1": "Wenn",
        "login_sent.body_2": "registriert ist oder angelegt werden darf, findest Du den Login-Link gleich dort.",
        "login_sent.footer": "Fünfzehn Minuten. Einmalig verwendbar. Nichts gekommen? Auch der Spam-Ordner lohnt einen Blick —",
        "login_sent.retry": "neu versuchen",

        # Edit calendar
        "edit_cal.back": "Zurück zum Dashboard",
        "edit_cal.kicker": "— Kalender bearbeiten",
        "edit_cal.workspace": "Workspace",
        "edit_cal.ics_label": "ICS-URL",
        "edit_cal.name_label": "Kalender-Name",
        "edit_cal.name_hint": "So erscheint er in Apple Calendar.",
        "edit_cal.date_prop": "Datums-Property",
        "edit_cal.desc_prop": "Beschreibung",
        "edit_cal.optional": "(optional)",
        "edit_cal.no_desc": "— keine —",
        "edit_cal.missing_suffix": "(nicht mehr vorhanden)",
        "edit_cal.save": "Änderungen speichern",
        "edit_cal.cancel": "Abbrechen",
        "edit_cal.unreachable_title": "Notion-Datenbank nicht erreichbar.",
        "edit_cal.unreachable_body": "Möglicherweise wurde die Freigabe entzogen. Prüfe die Verbindung im Dashboard.",
        "edit_cal.delete_confirm": "„{name}\" wird entfernt und die ICS-URL wird sofort ungültig. Abonnenten sehen den Kalender nicht mehr.",
        "edit_cal.delete_title": "Kalender löschen",
        "edit_cal.delete_label": "Ja, löschen",
        "edit_cal.delete": "Kalender löschen",

        # DB picker
        "picker.no_databases_title": "Keine Datenbanken gefunden.",
        "picker.no_databases_body": "Hast Du im OAuth-Dialog auch eine Datenbank freigegeben?",
        "picker.reconnect": "Nochmal verbinden",
        "picker.choose_database": "— Wähle eine Datenbank",
        "picker.date_column_one": "Datums-Spalte",
        "picker.date_column_many": "Datums-Spalten",

        # Property picker
        "picker.no_date_title": "Keine Datums-Spalte gefunden.",
        "picker.no_date_body_1": "Füge in Notion eine Property vom Typ",
        "picker.no_date_body_2": "hinzu und versuche es erneut.",
        "picker.create": "Anlegen",
        "picker.create_hint": "Die ICS-URL erscheint direkt danach.",

        # Imprint
        "imprint.kicker": "— Impressum",
        "imprint.title": "Rechtliches",
        "imprint.subtitle": "Angaben gemäß § 5 TMG",
        "imprint.name_missing": "nicht gesetzt.",
        "imprint.contact": "Kontakt",
        "imprint.responsible_title": "Verantwortlich für den Inhalt",
        "imprint.responsible_body": "nach § 55 Abs. 2 RStV",
        "imprint.disclaimer_title": "Haftungsausschluss",
        "imprint.disclaimer_body": "Die Inhalte dieses Dienstes wurden mit größtmöglicher Sorgfalt erstellt. Für Richtigkeit, Vollständigkeit und Aktualität kann jedoch keine Gewähr übernommen werden. Für die über Notion synchronisierten Daten trägt der jeweilige Nutzer die alleinige Verantwortung.",

        # Privacy
        "privacy.kicker": "— Datenschutz",
        "privacy.title_1": "Was wir speichern,",
        "privacy.title_em": "und was nicht.",
        "privacy.store_title": "Was wir speichern",
        "privacy.store_email": "E-Mail-Adresse",
        "privacy.store_email_body": "— für Login via Magic Link.",
        "privacy.store_ws": "Notion-Workspace-Name und -ID",
        "privacy.store_ws_body": "— zur Anzeige im Dashboard.",
        "privacy.store_token": "Notion-Access-Token",
        "privacy.store_token_enc": "Fernet-verschlüsselt",
        "privacy.store_token_body": ". Wird nur zum Abruf Deiner Kalender-Daten entschlüsselt.",
        "privacy.store_cfg": "Kalender-Konfiguration",
        "privacy.store_cfg_body": "— welche Datenbank, welche Properties.",
        "privacy.store_ip": "IP-Adresse",
        "privacy.store_ip_body": "— temporär für Rate-Limits, nicht dauerhaft.",
        "privacy.not_title_1": "Was wir",
        "privacy.not_title_em": "nicht",
        "privacy.not_title_2": "tun",
        "privacy.not_tracking": "Kein Tracking, keine Analytics, keine Werbe-Cookies.",
        "privacy.not_third_1": "Keine Weitergabe an Dritte — ausgenommen die technisch nötigen Dienstleister",
        "privacy.not_third_em": "(Notion, Resend)",
        "privacy.not_third_2": ".",
        "privacy.not_plain": "Dein Notion-Token verlässt unseren Server nicht im Klartext.",
        "privacy.rights_title": "Deine Rechte",
        "privacy.rights_body": "Trenn Deine Notion-Verbindungen im Dashboard und schreib uns — wir löschen alles Übrige.",
        "privacy.contact_1": "Für Kontakt siehe",
        "privacy.contact_link": "Impressum",
        "privacy.contact_2": ".",

        # Email
        "email.subject": "Dein Login-Link",
        "email.kicker": "— Willkommen zurück",
        "email.title_1": "Dein",
        "email.title_em": "Login-Link",
        "email.body_1": "Ein Klick genügt. Der Link ist",
        "email.body_15min": "fünfzehn Minuten",
        "email.body_2": "gültig und kann nur",
        "email.body_once": "einmal",
        "email.body_3": "verwendet werden.",
        "email.cta": "Jetzt einloggen",
        "email.or_copy": "— Oder URL kopieren",
        "email.unrequested": "Du hast diesen Login nicht angefordert? Dann ignoriere diese Nachricht — ohne Klick passiert nichts.",
        "email.text": "Dein Login-Link für Notion → Calendar:\n\n{link}\n\nDer Link ist 15 Minuten gültig und kann nur einmal verwendet werden.\nWenn du das nicht warst, ignoriere diese Mail.",

        # Flash messages
        "flash.welcome": "Willkommen, {email}.",
        "flash.logged_out": "Ausgeloggt. Bis bald.",
        "flash.ws_connected": "Workspace „{name}\" verbunden.",
        "flash.ws_disconnected": "Workspace „{name}\" getrennt.",
        "flash.cal_created": "„{name}\" angelegt. ICS-URL ist sofort aktiv.",
        "flash.cal_updated": "„{name}\" aktualisiert.",
        "flash.cal_deleted": "„{name}\" gelöscht.",

        # SEO (titles: 50–60 chars; descriptions: 150–160 chars)
        "seo.site_name": "Notion → Calendar",
        "seo.default_title": "Notion → Calendar — ICS-Feeds für Apple & Google Calendar",
        "seo.default_description": "Verbinde Notion-Datenbanken als ICS-Feed mit Apple Calendar und Google Calendar. Kostenlos, ohne Passwort, ohne Tracking.",
        "seo.landing_title": "Notion → Calendar — Notion als ICS-Feed in Apple Calendar",
        "seo.landing_description": "Verbinde eine Notion-Datenbank, wähle Deine Datums-Spalte und abonniere eine ICS-URL. Funktioniert mit Apple Calendar, Google Calendar und Outlook.",
        "seo.login_title": "Einloggen — Notion → Calendar",
        "seo.login_description": "Magic-Link-Login für Notion → Calendar. Kein Passwort, ein Klick genügt. Der Link ist 15 Minuten gültig.",
        "seo.imprint_title": "Impressum — Notion → Calendar",
        "seo.imprint_description": "Impressum gemäß § 5 TMG für den Dienst Notion → Calendar — Betreiber, Kontakt und Verantwortlichkeit.",
        "seo.privacy_title": "Datenschutz — Notion → Calendar",
        "seo.privacy_description": "Was wir speichern und was nicht. Kein Tracking, keine Analytics. Notion-Tokens sind Fernet-verschlüsselt. Deine Rechte im Überblick.",
    },
    "en": {
        # Nav / shared
        "nav.dashboard": "Dashboard",
        "nav.logout": "Log out",
        "nav.login": "Sign in",
        "nav.lang_label": "Language",
        "footer.made_with_care": "Made with care",
        "footer.imprint": "Imprint",
        "footer.privacy": "Privacy",
        "toast.close": "Close",
        "modal.confirm_kicker": "— Please confirm",
        "modal.confirm_title": "Sure?",
        "modal.confirm_body": "Really perform this action?",
        "modal.cancel": "Cancel",
        "modal.confirm": "Confirm",

        # Landing
        "landing.kicker": "A small, careful tool",
        "landing.title_1": "Your Notion calendar,",
        "landing.title_em": "wherever",
        "landing.title_2": "you need it.",
        "landing.lead": "Connect a Notion database, pick your date column — and get an ICS subscription URL that Apple Calendar, Google Calendar and every other calendar client understands.",
        "landing.cta_start": "Get started",
        "landing.cta_free": "Free · no password",
        "landing.how_kicker": "— How it works",
        "landing.step1_title": "Sign in",
        "landing.step1_body_1": "Enter your email. We send you a link —",
        "landing.step1_body_em": "one click is enough",
        "landing.step1_body_2": ". No password, nothing to forget.",
        "landing.step2_title": "Connect Notion",
        "landing.step2_body": "Official OAuth connection. You decide which databases we get to see in the first place.",
        "landing.step3_title": "Subscribe",
        "landing.step3_body_1": "Copy the URL, paste it into Apple Calendar.",
        "landing.step3_body_em": "Done.",
        "landing.step3_body_2": "Changes in Notion appear automatically.",
        "landing.quote": "\"Calendars deserve care.\u00a0 This is not a platform — it is a piece of craft that solves one concrete task elegantly.\"",
        "landing.live_title_1": "Notion data,",
        "landing.live_title_em": "live",
        "landing.live_title_2": "in your calendar.",
        "landing.live_body": "Every change in your Notion database appears automatically in your calendar. Apple\u00a0Calendar, Google\u00a0Calendar — all via ICS.",
        "landing.preview_month": "April 2026",
        "weekday.mon": "Mon",
        "weekday.tue": "Tue",
        "weekday.wed": "Wed",
        "weekday.thu": "Thu",
        "weekday.fri": "Fri",
        "weekday.sat": "Sat",
        "weekday.sun": "Sun",

        # Dashboard
        "dashboard.kicker": "— Dashboard",
        "dashboard.title_1": "Your",
        "dashboard.title_em": "calendars",
        "dashboard.lead": "Connect Notion workspaces and choose per database which date gets exported.",
        "dashboard.empty_title": "No connection yet",
        "dashboard.empty_body": "Link your Notion workspace via OAuth. You decide which pages we may see.",
        "dashboard.connect_notion": "Connect Notion",
        "dashboard.workspace_label": "Notion workspace",
        "dashboard.disconnect": "disconnect",
        "dashboard.disconnect_confirm": "If you disconnect this workspace, all associated calendar feeds become invalid immediately. Sure?",
        "dashboard.disconnect_title": "Disconnect workspace",
        "dashboard.disconnect_label": "Yes, disconnect",
        "dashboard.no_calendars": "No calendars from this workspace yet. Add one below.",
        "dashboard.copy": "copy",
        "dashboard.copied": "copied ✓",
        "dashboard.edit": "edit",
        "dashboard.add_calendar": "Add calendar",
        "dashboard.loading_databases": "Loading databases from Notion …",
        "dashboard.connect_another": "Connect another workspace",

        # Login
        "login.kicker": "— Welcome back",
        "login.title": "Sign in",
        "login.lead_1": "We send you a",
        "login.lead_em": "link",
        "login.lead_2": ". Valid for fifteen minutes.",
        "login.email_label": "Email",
        "login.email_placeholder": "you@example.com",
        "login.submit": "Send link",
        "login.new_here": "New here? That's fine too — we'll create your account automatically.",
        "login.error_invalid": "Link invalid or expired.",

        # Login sent
        "login_sent.title": "Check your inbox.",
        "login_sent.body_1": "If",
        "login_sent.body_2": "is registered or may be created, you'll find the sign-in link right there.",
        "login_sent.footer": "Fifteen minutes. Single use. Nothing arrived? The spam folder is worth a glance —",
        "login_sent.retry": "try again",

        # Edit calendar
        "edit_cal.back": "Back to dashboard",
        "edit_cal.kicker": "— Edit calendar",
        "edit_cal.workspace": "Workspace",
        "edit_cal.ics_label": "ICS URL",
        "edit_cal.name_label": "Calendar name",
        "edit_cal.name_hint": "This is how it appears in Apple Calendar.",
        "edit_cal.date_prop": "Date property",
        "edit_cal.desc_prop": "Description",
        "edit_cal.optional": "(optional)",
        "edit_cal.no_desc": "— none —",
        "edit_cal.missing_suffix": "(no longer present)",
        "edit_cal.save": "Save changes",
        "edit_cal.cancel": "Cancel",
        "edit_cal.unreachable_title": "Notion database unreachable.",
        "edit_cal.unreachable_body": "The access may have been revoked. Check the connection in the dashboard.",
        "edit_cal.delete_confirm": "\"{name}\" will be removed and the ICS URL becomes invalid immediately. Subscribers will no longer see the calendar.",
        "edit_cal.delete_title": "Delete calendar",
        "edit_cal.delete_label": "Yes, delete",
        "edit_cal.delete": "Delete calendar",

        # DB picker
        "picker.no_databases_title": "No databases found.",
        "picker.no_databases_body": "Did you also share a database in the OAuth dialog?",
        "picker.reconnect": "Connect again",
        "picker.choose_database": "— Choose a database",
        "picker.date_column_one": "date column",
        "picker.date_column_many": "date columns",

        # Property picker
        "picker.no_date_title": "No date column found.",
        "picker.no_date_body_1": "Add a property of type",
        "picker.no_date_body_2": "in Notion and try again.",
        "picker.create": "Create",
        "picker.create_hint": "The ICS URL appears right after.",

        # Imprint
        "imprint.kicker": "— Imprint",
        "imprint.title": "Legal",
        "imprint.subtitle": "Information pursuant to § 5 TMG (German Telemedia Act)",
        "imprint.name_missing": "not set.",
        "imprint.contact": "Contact",
        "imprint.responsible_title": "Responsible for content",
        "imprint.responsible_body": "under § 55 para. 2 RStV",
        "imprint.disclaimer_title": "Disclaimer",
        "imprint.disclaimer_body": "The contents of this service were created with the greatest possible care. However, no guarantee can be given for the accuracy, completeness and topicality. The user alone is responsible for the data synchronized via Notion.",

        # Privacy
        "privacy.kicker": "— Privacy",
        "privacy.title_1": "What we store,",
        "privacy.title_em": "and what we don't.",
        "privacy.store_title": "What we store",
        "privacy.store_email": "Email address",
        "privacy.store_email_body": "— for sign-in via magic link.",
        "privacy.store_ws": "Notion workspace name and ID",
        "privacy.store_ws_body": "— to display in the dashboard.",
        "privacy.store_token": "Notion access token",
        "privacy.store_token_enc": "Fernet-encrypted",
        "privacy.store_token_body": ". Decrypted only to fetch your calendar data.",
        "privacy.store_cfg": "Calendar configuration",
        "privacy.store_cfg_body": "— which database, which properties.",
        "privacy.store_ip": "IP address",
        "privacy.store_ip_body": "— temporarily for rate limits, not permanently.",
        "privacy.not_title_1": "What we",
        "privacy.not_title_em": "don't",
        "privacy.not_title_2": "do",
        "privacy.not_tracking": "No tracking, no analytics, no advertising cookies.",
        "privacy.not_third_1": "No sharing with third parties — except the technically necessary providers",
        "privacy.not_third_em": "(Notion, Resend)",
        "privacy.not_third_2": ".",
        "privacy.not_plain": "Your Notion token never leaves our server in plain text.",
        "privacy.rights_title": "Your rights",
        "privacy.rights_body": "Disconnect your Notion connections in the dashboard and write us — we'll delete the rest.",
        "privacy.contact_1": "For contact see",
        "privacy.contact_link": "Imprint",
        "privacy.contact_2": ".",

        # Email
        "email.subject": "Your sign-in link",
        "email.kicker": "— Welcome back",
        "email.title_1": "Your",
        "email.title_em": "sign-in link",
        "email.body_1": "One click is enough. The link is valid for",
        "email.body_15min": "fifteen minutes",
        "email.body_2": "and can only be used",
        "email.body_once": "once",
        "email.body_3": ".",
        "email.cta": "Sign in now",
        "email.or_copy": "— Or copy URL",
        "email.unrequested": "You didn't request this sign-in? Then ignore this message — without a click, nothing happens.",
        "email.text": "Your sign-in link for Notion → Calendar:\n\n{link}\n\nThe link is valid for 15 minutes and can only be used once.\nIf this wasn't you, ignore this email.",

        # Flash messages
        "flash.welcome": "Welcome, {email}.",
        "flash.logged_out": "Logged out. See you soon.",
        "flash.ws_connected": "Workspace \"{name}\" connected.",
        "flash.ws_disconnected": "Workspace \"{name}\" disconnected.",
        "flash.cal_created": "\"{name}\" created. ICS URL is active immediately.",
        "flash.cal_updated": "\"{name}\" updated.",
        "flash.cal_deleted": "\"{name}\" deleted.",

        # SEO
        "seo.site_name": "Notion → Calendar",
        "seo.default_title": "Notion → Calendar — ICS feeds for Apple & Google Calendar",
        "seo.default_description": "Connect Notion databases as an ICS feed to Apple Calendar and Google Calendar. Free, no password, no tracking.",
        "seo.landing_title": "Notion → Calendar — Notion as an ICS feed in Apple Calendar",
        "seo.landing_description": "Connect a Notion database, pick your date column and subscribe to an ICS URL. Works with Apple Calendar, Google Calendar and Outlook.",
        "seo.login_title": "Sign in — Notion → Calendar",
        "seo.login_description": "Magic-link sign-in for Notion → Calendar. No password, one click is enough. The link is valid for 15 minutes.",
        "seo.imprint_title": "Imprint — Notion → Calendar",
        "seo.imprint_description": "Imprint pursuant to § 5 TMG for the Notion → Calendar service — operator, contact and accountability.",
        "seo.privacy_title": "Privacy — Notion → Calendar",
        "seo.privacy_description": "What we store and what we don't. No tracking, no analytics. Notion tokens are Fernet-encrypted. Your rights at a glance.",
    },
}


def _parse_accept_language(header: str) -> str | None:
    for part in header.split(","):
        code = part.split(";")[0].strip().lower()
        if not code:
            continue
        primary = code.split("-")[0]
        if primary in SUPPORTED:
            return primary
    return None


def get_locale(request: Request) -> str:
    """Locale is set by LocaleMiddleware via URL prefix (`/en/...`)."""
    locale = request.scope.get("locale")
    if locale in SUPPORTED:
        return locale
    return DEFAULT


def get_path_no_locale(request: Request) -> str:
    path = request.scope.get("path_no_locale")
    if path:
        return path
    return request.url.path


def strip_locale_prefix(path: str) -> tuple[str, str]:
    """Return (locale, path_without_prefix). Used for parsing referer URLs in /lang switch."""
    for code in SUPPORTED:
        if code == DEFAULT:
            continue
        prefix = f"/{code}"
        if path == prefix:
            return code, "/"
        if path.startswith(f"{prefix}/"):
            return code, path[len(prefix):]
    return DEFAULT, path


def build_locale_url(path_no_locale: str, target_locale: str) -> str:
    """Given a path without locale prefix, build URL for the target locale."""
    if target_locale == DEFAULT:
        return path_no_locale
    if not path_no_locale.startswith("/"):
        path_no_locale = "/" + path_no_locale
    return f"/{target_locale}{path_no_locale}"


def lredirect(request: Request, path: str) -> str:
    """Build a locale-aware redirect target matching the request's current locale."""
    return build_locale_url(path, get_locale(request))


def translate(key: str, locale: str, **params) -> str:
    bundle = TRANSLATIONS.get(locale) or TRANSLATIONS[DEFAULT]
    text = bundle.get(key)
    if text is None and locale != DEFAULT:
        text = TRANSLATIONS[DEFAULT].get(key)
    if text is None:
        return key
    if params:
        try:
            return text.format(**params)
        except (KeyError, IndexError):
            return text
    return text


def make_translator(locale: str):
    def _(key: str, **params) -> str:
        return translate(key, locale, **params)
    return _
