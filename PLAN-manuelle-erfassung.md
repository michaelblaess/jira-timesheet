# Plan: Manuelle Zeiterfassung

Stand: 24.07.2026. Grundlage: Ticket DMZ-17024 (Stundentabelle im ersten
Kommentar) und `Beispiel.xlsx` im Repo-Root.

## Ziel

Zeiten, die nicht in Jira gebucht sind (z. B. DMZ-17024, 63,25 h über Juni/Juli
2026), direkt im Tool erfassen — statt sie hinterher von Hand ins Excel zu
tippen. Die Einträge fließen überall mit (Tabelle, Kalender, Jahresansicht,
Soll/Ist, Excel, PDF) und sind optisch als manuell erkennbar.

## Entscheidungen (mit Michael abgestimmt)

| Thema | Entscheidung |
| --- | --- |
| Datenmodell | Kein zweiter Typ — `WorklogEntry` bekommt `manual: bool` und `customer: str` |
| Persistenz | **SQLite** (`~/.jira-timesheet/manual-entries.db`), Muster wie death-proof |
| Spalte „Kunde" | Kommt fest in den Export |
| Markierung | Setting: Checkbox „Manuelle Einträge farblich markieren" + Farbfeld (Hex/RGB), Default Rot |
| Spalten-Konfiguration | Eigener Settings-Tab: pro Spalte Checkbox (aktiv) + Textfeld (Bezeichnung), Defaults vorbelegt |
| Beschreibung aus Jira nachladen | In dieser Phase **nicht** |

## Kernidee

Manuelle Einträge sind ganz normale `WorklogEntry`-Objekte mit `manual=True`.
Damit zählen sie automatisch in jede Summe. Nur die Darstellung verzweigt.

**Kritisch:** Sie dürfen **nie** in den Jira-Cache (`CacheService`). Der Cache
ist ein Abbild dessen, was Jira geliefert hat. Landen manuelle Einträge dort,
werden sie beim nächsten `save` überschrieben oder beim Refresh doppelt
gezählt. Also: getrennt in SQLite, Merge **nach** dem Cache-Load.

### Merge-Punkte

1. `app.py` — vor `TimesheetService.build_timesheet` und damit **vor**
   `worked_dates = {e.date for e in entries}`. Sonst meldet die
   Lückenerkennung einen Tag mit ausschließlich manuellen Stunden weiter als
   „kein Eintrag".
2. `app.py`, Jahresansicht — die Monatsschleife summiert aus dem Cache. Ohne
   Merge fehlen dort für Juni/Juli 2026 rund 63 h.
3. Excel/PDF brauchen nichts: sie arbeiten auf `self._timesheet`.

## Datenmodell

### `WorklogEntry` (models/timesheet.py)

Zwei neue Felder mit Defaults — `CacheService` serialisiert Feld für Feld,
alte Cache-Dateien bleiben lesbar:

```python
manual: bool = False
customer: str = ""
```

`customer` bleibt bei Jira-Einträgen leer; die Exporte fallen dann auf das
Setting `default_customer` („Vertrieb") zurück.

### SQLite-Schema (`~/.jira-timesheet/manual-entries.db`)

```sql
CREATE TABLE IF NOT EXISTS manual_entries (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    entry_date  TEXT NOT NULL,              -- ISO YYYY-MM-DD
    ticket      TEXT NOT NULL DEFAULT '',
    summary     TEXT NOT NULL DEFAULT '',
    customer    TEXT NOT NULL DEFAULT '',
    hours       REAL NOT NULL DEFAULT 0,
    created_at  TEXT NOT NULL DEFAULT '',
    updated_at  TEXT NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS idx_manual_entries_date ON manual_entries(entry_date);
```

Lock-Behandlung (death-proof-Muster):

- eine Verbindung pro App-Instanz, `check_same_thread=False`
- `PRAGMA journal_mode=WAL` — Leser blockieren Schreiber nicht
- `PRAGMA busy_timeout=5000` — statt sofortigem „database is locked"
- `row_factory = sqlite3.Row`
- Commit nach jedem Schreibvorgang, `close()` in `on_unmount`
- idempotente `_migrate()` mit `PRAGMA table_info`-Guards

## Spalten-Konfiguration

Acht Spalten, Reihenfolge wie in `Beispiel.xlsx`:

| Key | Default-Bezeichnung | Excel-Breite | PDF-Breite (mm) |
| --- | --- | --- | --- |
| `week` | KW | 5 | 10 |
| `weekday` | Tag | 6 | 10 |
| `date` | Datum | 11 | 16 |
| `ticket` | Ticket | 12 | 24 |
| `description` | Beschreibung | Flex | Flex |
| `customer` | Kunde | 20 | 30 |
| `hours` | Aufwand (h) | 12 | 25 |
| `day_hours` | Tagessumme (h) | 15 | 25 |

- Beschreibung ist die Flex-Spalte: bekommt, was die aktiven Spalten übrig
  lassen (PDF: 277 mm − Rest bei A4 quer).
- Persistenz in `settings.json` als `export_columns`. Beim Laden mit den
  Defaults gemerged, damit später ergänzte Spalten automatisch auftauchen.
- Gilt für **Excel und PDF**. Die TUI-Tabelle behält ihre i18n-Kopfzeilen.

## Settings (neu)

| Schlüssel | Typ | Default |
| --- | --- | --- |
| `export_columns` | Liste aus `{key, enabled, label}` | siehe Tabelle oben |
| `mark_manual_entries` | bool | `True` |
| `manual_entry_color` | str | `FF0000` (wie in `Beispiel.xlsx`) |
| `default_customer` | str | `Vertrieb` |

Farbeingabe akzeptiert `#RRGGBB`, `RRGGBB` und `R,G,B`; intern normalisiert
auf `RRGGBB`.

## Dialog

`ManualEntryScreen(ModalScreen[ManualEntry | None])`, Taste `m` (frei geprüft).

Felder: Datum, Ticket, Beschreibung, Kunde, Aufwand. Buttons „Speichern"
(primary) / „Abbrechen" — kanonische Beschriftungen.

- Datum vorbelegt mit dem Tag unter dem Cursor, sonst heute.
- Kunde vorbelegt mit `default_customer`.
- Aufwand tolerant geparst: `3h 30m`, `5h`, `15m`, `3:30`, `3,5`, `3.5`.
- Cursor auf einer manuellen Zeile: `m` öffnet sie zum Bearbeiten,
  `DEL` löscht (destruktiv → keine Buchstabentaste).

## Markierung

Ist `mark_manual_entries` an, werden manuelle Zeilen fett in
`manual_entry_color` dargestellt:

- **TUI-Tabelle:** Ticket, Beschreibung und Aufwand der Zeile.
- **Excel:** dieselben Zellen (`Font(bold=True, color=...)`) — entspricht
  Zeile 110/115/119/123/127 in `Beispiel.xlsx`.
- **PDF:** `set_text_color` für die Zeile.

## Umsetzungsreihenfolge

1. Modell: `WorklogEntry` um `manual`/`customer` erweitern
2. `models/export_column.py` — Spaltendefinition + Defaults + Merge
3. `models/settings.py` — vier neue Schlüssel, defensiv geladen
4. `services/manual_entry_service.py` — SQLite-Repository
5. `screens/manual_entry_screen.py` — Dialog inkl. Aufwand-Parser
6. `widgets/timesheet_table.py` — Markierung
7. `services/excel_exporter.py` / `pdf_exporter.py` — Spaltenkonfiguration,
   Kunde, Markierung
8. `screens/settings_screen.py` — Tab „Spalten" + Markierungs-Optionen
9. `app.py` — Merge an beiden Stellen, Bindings, Dialog-Verdrahtung
10. Locale de/en
11. Tests
12. Juli-Werte aus DMZ-17024 in die SQLite-Tabelle eintragen

## Juli-Werte aus DMZ-17024 (Schritt 12)

| Datum | Stunden |
| --- | --- |
| 01.07.2026 | 10,00 |
| 02.07.2026 | 9,00 |
| 03.07.2026 | 5,50 |
| 06.07.2026 | 5,00 |
| 07.07.2026 | 3,50 |
| 08.07.2026 | 5,50 |
| 13.07.2026 | 0,25 |
| **Summe** | **38,75** |

Juni (24,50 h: 24.06. 3,00 / 25.06. 6,00 / 26.06. 3,50 / 29.06. 8,00 /
30.06. 8,00) ist bereits von Hand im Excel nachgetragen — auf Zuruf ebenfalls
nachtragbar.
