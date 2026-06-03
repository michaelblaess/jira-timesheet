# Jira Timesheet

<p align="center">
  <img src="docs/flags/gb.svg" height="13" alt=""> <a href="README.md">English</a> ·
  <img src="docs/flags/de.svg" height="13" alt=""> <b>Deutsch</b>
</p>

---

[![Stars](https://img.shields.io/github/stars/michaelblaess/jira-timesheet?logo=github&logoColor=white&color=fbbf24)](https://github.com/michaelblaess/jira-timesheet/stargazers)
[![Forks](https://img.shields.io/github/forks/michaelblaess/jira-timesheet?logo=github&logoColor=white&color=34d399)](https://github.com/michaelblaess/jira-timesheet/network/members)
[![Issues](https://img.shields.io/github/issues/michaelblaess/jira-timesheet?logo=github&logoColor=white&color=f87171)](https://github.com/michaelblaess/jira-timesheet/issues)
[![Pull Requests](https://img.shields.io/github/issues-pr/michaelblaess/jira-timesheet?logo=github&logoColor=white&color=a78bfa)](https://github.com/michaelblaess/jira-timesheet/pulls)

[![Last Commit](https://img.shields.io/github/last-commit/michaelblaess/jira-timesheet?logo=git&logoColor=white&color=3b82f6)](https://github.com/michaelblaess/jira-timesheet/commits/main)
[![License](https://img.shields.io/badge/license-Apache_2.0-3b82f6)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12+-3b82f6?logo=python&logoColor=white)](https://www.python.org/)

Terminal-basierte Anwendung (TUI) zum Generieren von Stundenzetteln aus Jira Worklogs.

> **Disclaimer:** Dieses Projekt ist **nicht** von Atlassian entwickelt, unterstützt oder autorisiert. "Jira" und "Atlassian" sind eingetragene Markenzeichen von [Atlassian Corporation](https://www.atlassian.com/). Dieses Tool nutzt die öffentliche Jira REST API und steht in keiner Verbindung zu Atlassian.

## Screenshots

Die Oberfläche bringt Retro-Themes mit. Jede Ansicht ist unten in mehreren davon zu sehen.

### Listenansicht

<p align="center">
  <img src="docs/screenshots/01-main-beastie.png" width="32%" alt="Listenansicht (Beastie)">
  <img src="docs/screenshots/01-main-bebox.png" width="32%" alt="Listenansicht (BeBox)">
  <img src="docs/screenshots/01-main-classic-terminal.png" width="32%" alt="Listenansicht (Classic Terminal)">
  <img src="docs/screenshots/01-main-corleone.png" width="32%" alt="Listenansicht (Corleone)">
  <img src="docs/screenshots/01-main-gemstone.png" width="32%" alt="Listenansicht (Gemstone)">
  <img src="docs/screenshots/01-main-metropolis.png" width="32%" alt="Listenansicht (Metropolis)">
  <img src="docs/screenshots/01-main-miami.png" width="32%" alt="Listenansicht (Miami)">
</p>

### Kalenderansicht

<p align="center">
  <img src="docs/screenshots/02-month-view-beastie.png" width="32%" alt="Kalenderansicht (Beastie)">
  <img src="docs/screenshots/02-month-view-bebox.png" width="32%" alt="Kalenderansicht (BeBox)">
  <img src="docs/screenshots/02-month-view-classic-terminal.png" width="32%" alt="Kalenderansicht (Classic Terminal)">
  <img src="docs/screenshots/02-month-view-corleone.png" width="32%" alt="Kalenderansicht (Corleone)">
  <img src="docs/screenshots/02-month-view-gemstone.png" width="32%" alt="Kalenderansicht (Gemstone)">
  <img src="docs/screenshots/02-month-view-metropolis.png" width="32%" alt="Kalenderansicht (Metropolis)">
  <img src="docs/screenshots/02-month-view-miami.png" width="32%" alt="Kalenderansicht (Miami)">
</p>

### Jahresansicht mit Forecast

<p align="center">
  <img src="docs/screenshots/03-year-view-beastie.png" width="32%" alt="Jahresansicht (Beastie)">
  <img src="docs/screenshots/03-year-view-bebox.png" width="32%" alt="Jahresansicht (BeBox)">
  <img src="docs/screenshots/03-year-view-classic-terminal.png" width="32%" alt="Jahresansicht (Classic Terminal)">
  <img src="docs/screenshots/03-year-view-corleone.png" width="32%" alt="Jahresansicht (Corleone)">
  <img src="docs/screenshots/03-year-view-gemstone.png" width="32%" alt="Jahresansicht (Gemstone)">
  <img src="docs/screenshots/03-year-view-metropolis.png" width="32%" alt="Jahresansicht (Metropolis)">
  <img src="docs/screenshots/03-year-view-miami.png" width="32%" alt="Jahresansicht (Miami)">
</p>

### Ticket-Details

<p align="center">
  <img src="docs/screenshots/04-details-beastie.png" width="32%" alt="Ticket-Details (Beastie)">
  <img src="docs/screenshots/04-details-bebox.png" width="32%" alt="Ticket-Details (BeBox)">
  <img src="docs/screenshots/04-details-classic-terminal.png" width="32%" alt="Ticket-Details (Classic Terminal)">
  <img src="docs/screenshots/04-details-metropolis.png" width="32%" alt="Ticket-Details (Metropolis)">
</p>

### Einstellungen

<p align="center">
  <img src="docs/screenshots/05-settings-beastie.png" width="32%" alt="Einstellungen - Sprache (Beastie)">
  <img src="docs/screenshots/05-settings-classic-terminal.png" width="32%" alt="Einstellungen - Sprache (Classic Terminal)">
  <img src="docs/screenshots/05-settings-corleone.png" width="32%" alt="Einstellungen - Sprache (Corleone)">
  <img src="docs/screenshots/05-settings-gemstone-1.png" width="32%" alt="Einstellungen - Sprache (Gemstone)">
  <img src="docs/screenshots/05-settings-gemstone-2.png" width="32%" alt="Einstellungen - Berechnung (Gemstone)">
  <img src="docs/screenshots/05-settings-metropolis.png" width="32%" alt="Einstellungen - Berechnung (Metropolis)">
  <img src="docs/screenshots/05-settings-metropolis-02.png" width="32%" alt="Einstellungen - Export (Metropolis)">
  <img src="docs/screenshots/05-settings-metropolis-03.png" width="32%" alt="Einstellungen - Jira (Metropolis)">
</p>

### Info

<p align="center">
  <img src="docs/screenshots/06-info-beastie.png" width="32%" alt="Info-Dialog (Beastie)">
  <img src="docs/screenshots/06-info-bebox.png" width="32%" alt="Info-Dialog (BeBox)">
  <img src="docs/screenshots/06-info-metropolis.png" width="32%" alt="Info-Dialog (Metropolis)">
</p>

## Features

- **Jira Integration** — Worklogs per REST API abrufen (Bearer Token Auth)
- **Listenansicht** — Tabellarisch mit KW, Wochentag, Tagesgruppen, Soll/Ist-Stunden
- **Suche / Filter** — Live-Filter nach Ticket-ID oder Beschreibung (`/` zum Fokussieren, Verlauf mit Dropdown)
- **Kalenderansicht** — Monatskalender mit farbcodierten Tageskacheln
- **Tab-Navigation** — Zwischen Ansichten wechseln mit TAB oder Klick
- **Jahresansicht** — 12 Monatskacheln mit Progressbar und Forecast (J)
- **Excel-Export** — Formatierter Stundenzettel mit Logo und Unterschriftszeile
- **PDF-Export** — Adobe-signierbar, Unicode-Schriftart (Arial)
- **Feiertage** — Deutsche Feiertage pro Bundesland, Lücken-Erkennung
- **Soll/Ist** — Arbeitszeitvergleich mit Differenz-Anzeige
- **Ticket-Details** — Enter/D zeigt Status, Typ, Bearbeiter, Komponenten im Log
- **Anonymisierung** — Daten per Tastendruck anonymisieren für sichere Screenshots
- **Worklog-Cache** — Abgeschlossene Monate gecached, Jahresansicht lädt sofort
- **Zweisprachige Oberfläche** — Deutsch/Englisch, umschaltbar via `--lang` oder Settings-Dialog
- **31 Retro-Themes** — via Theme-Picker (Ctrl+P), siehe [textual-themes](https://github.com/michaelblaess/textual-themes)

## Installation

### One-Click Install

**Windows (PowerShell):**
```powershell
irm https://raw.githubusercontent.com/michaelblaess/jira-timesheet/main/install.ps1 | iex
```

**Linux/macOS:**
```bash
curl -fsSL https://raw.githubusercontent.com/michaelblaess/jira-timesheet/main/install.sh | bash
```

Danach einfach `jira-timesheet` im Terminal eingeben.

### Manuelle Installation

```bash
git clone https://github.com/michaelblaess/jira-timesheet.git
cd jira-timesheet
setup.bat
run.bat
```

## Benutzung

```bash
jira-timesheet
```

Die Oberflächensprache (Deutsch/Englisch) folgt dem `--lang`-Flag — die Wahl wird gespeichert und ist auch im Settings-Dialog umschaltbar:

```bash
jira-timesheet --lang en
```

Beim ersten Start `S` für Settings drücken und konfigurieren:
- Jira Host URL
- Bearer Token
- E-Mail (Jira Username)
- Bundesland (Feiertage)

Dann `G` zum Generieren des Stundenzettels.

## Tastenkürzel

| Taste | Aktion |
|-------|--------|
| G | Stundenzettel generieren |
| E | Excel-Export |
| P | PDF-Export |
| D | Ticket-Details anzeigen |
| TAB | Tab wechseln (Liste / Kalender) |
| / | Suchfeld fokussieren (Listenansicht) |
| R | Cache zurücksetzen |
| J | Jahresansicht mit Forecast |
| A | Daten anonymisieren |
| < / > | Monat wechseln |
| S | Settings |
| I | Info |
| C | Log kopieren |
| L | Log ein/ausblenden |
| Ctrl+P | Theme wechseln |
| Q | Beenden |

## Konfiguration

Settings werden in `~/.jira-timesheet/settings.json` gespeichert:

| Einstellung | Beschreibung | Default |
|-------------|-------------|---------|
| Jira Host | URL der Jira-Instanz | — |
| Token | Bearer Token für Authentifizierung | — |
| E-Mail | Jira Username | — |
| Bundesland | Für Feiertagsberechnung | SN |
| Soll-Stunden/Tag | Arbeitsstunden pro Tag | 8.0 |
| Max. Jahresstunden | Obergrenze für Progressbar | 1720 |
| Urlaubstage | Für Jahres-Forecast | 30 |
| Stundensatz | Netto, nur TUI-Anzeige | 0 (aus) |
| Jahr | Für Jahresansicht | aktuelles Jahr |
| Soll-Stunden im Export | Zeigt Soll-Zeile in Excel/PDF | false |
| Ticket-Links im Export | Hyperlinks in Excel/PDF | false |
| Sprache | Oberflächensprache (de / en) | de |

## Tech Stack

- [Python](https://python.org) >= 3.12
- [Textual](https://textual.textualize.io) — TUI Framework
- [Rich](https://rich.readthedocs.io) — Terminal Formatting
- [httpx](https://www.python-httpx.org) — Async HTTP Client
- [openpyxl](https://openpyxl.readthedocs.io) — Excel Export
- [fpdf2](https://py-pdf.github.io/fpdf2) — PDF Export
- [holidays](https://python-holidays.readthedocs.io) — Feiertagsberechnung

## Lizenz

Apache License 2.0

---

> **Trademark Notice:** "Jira" is a registered trademark of [Atlassian Corporation](https://www.atlassian.com/). This project is not affiliated with, endorsed by, or sponsored by Atlassian.
