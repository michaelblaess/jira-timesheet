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

Terminal-basierte Anwendung (TUI) für Stundenzettel aus Jira-Worklogs — inklusive manueller Nacherfassung für Zeiten, die nicht in Jira gebucht sind.

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

- **Jira Cloud & Data Center** — Worklogs per REST API; standardmäßig Jira Cloud (v3, Basic-Auth mit API-Token), per Schalter auch altes Jira Server/Data Center (v2, Bearer-Token)
- **Budget-Feld automatisch ermitteln** — Findet das Budget-Custom-Field bei Jira Cloud automatisch (kein manuelles Nachschlagen der ID)
- **Listenansicht** — Tabellarisch mit KW, Wochentag, Tagesgruppen, Soll/Ist-Stunden
- **Suche / Filter** — Live-Filter nach Ticket-ID oder Beschreibung (`/` zum Fokussieren, Verlauf mit Dropdown)
- **Spaltenbreiten ziehen** — Trennlinie im Spaltenkopf mit der Maus ziehen; Doppelklick setzt zurück, die Breiten werden gespeichert. Die Beschreibung füllt sonst automatisch die freie Breite
- **Manuelle Zeiterfassung** — Zeiten, die nicht in Jira gebucht sind, per Dialog erfassen (`m`), bearbeiten und löschen (`ENTF`); gespeichert in SQLite, farblich markiert in Liste, Excel und PDF
- **Konfigurierbare Export-Spalten** — jede Spalte an-/abwählbar und frei benennbar (Settings-Tab "Spalten"), inklusive Kunden-Spalte
- **Kalenderansicht** — Monatskalender mit farbcodierten Tageskacheln
- **Tab-Navigation** — Zwischen Ansichten wechseln mit TAB oder Klick
- **Jahresansicht** — 12 Monatskacheln mit Progressbar und Forecast (J)
- **Excel-Export** — Formatierter Stundenzettel mit Logo und Unterschriftszeile
- **PDF-Export** — Adobe-signierbar, Unicode-Schriftart (Arial)
- **Feiertage** — Deutsche Feiertage pro Bundesland, Lücken-Erkennung
- **Soll/Ist** — Arbeitszeitvergleich mit Differenz-Anzeige
- **MwSt konfigurierbar** — MwSt-Satz als Setting für die Netto/Brutto-Berechnung (Standard 19 %)
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
- Jira Host URL (Cloud: die kanonische `https://deine-firma.atlassian.net`)
- Token — Jira Cloud: ein API-Token von [id.atlassian.com](https://id.atlassian.com/manage-profile/security/api-tokens); Data Center: ein Bearer-Token (PAT)
- E-Mail / Login — Cloud: deine Atlassian-Login-Mail; Data Center: dein Jira-Benutzername
- **Jira-Modus** — für Jira Cloud aus lassen, für altes Server/Data Center anhaken
- Budget-Custom-Field — bei Cloud per **Automatisch ermitteln** befüllen lassen
- Bundesland (Feiertage)

Dann `G` zum Generieren des Stundenzettels.

### Zeiten erfassen, die nicht in Jira stehen

Nicht jede Stunde landet als Worklog in Jira. Mit `M` öffnet sich ein Dialog für
Datum, Ticket, Beschreibung, Kunde und Aufwand. Der Aufwand darf so geschrieben
werden, wie man ihn ohnehin notiert: `3h 30m`, `3:30`, `3,5` oder `45m`.

Diese Einträge landen in einer eigenen SQLite-Datei
(`~/.jira-timesheet/manual-entries.db`) und **nie** im Jira-Cache. Sie zählen
überall mit — Tagessumme, Monatssumme, Soll/Ist, Kalender, Jahresansicht,
Excel und PDF — und sind farblich markiert, damit auf einen Blick klar ist,
was aus Jira kommt und was nicht. Wie viel davon manuell erfasst wurde, steht
in der Kennzahlen-Zeile, in jeder Monatskachel der Jahresansicht und in deren
Jahres-Summe.

Steht der Cursor auf einem manuellen Eintrag, öffnet `M` ihn zum Bearbeiten;
`ENTF` löscht ihn nach einer Rückfrage. Im Bearbeiten-Dialog gibt es zusätzlich
einen **Löschen**-Button, der dieselbe Rückfrage stellt.

Ein **Rechtsklick** auf eine Zeile öffnet ein Kontextmenü: Details anzeigen,
Ticket im Browser öffnen, Zeit für diesen Tag erfassen, Eintrag bearbeiten oder
löschen. Was auf die angeklickte Zeile nicht zutrifft, ist ausgegraut - die
Punkte sitzen also immer an derselben Stelle. Das funktioniert auch auf einer
Lückenzeile (`— kein Eintrag —`), um dort direkt eine Zeit nachzutragen.

### Export-Spalten anpassen

Im Settings-Tab **Spalten** hat jede der acht Spalten (KW, Tag, Datum, Ticket,
Beschreibung, Kunde, Aufwand, Tagessumme) zwei Häkchen: **Anzeige** steuert die
Listenansicht, **Export** die Excel- und PDF-Datei. Beides ist getrennt
schaltbar - eine Spalte kann also im Export stehen, ohne die Liste zu füllen.

Das Textfeld daneben ist die Überschrift **im Export**; die Liste behält ihre
übersetzten Überschriften, damit sie beim Sprachwechsel mitgeht. Die
Beschreibung ist die flexible Spalte: sie bekommt die Breite, die die übrigen
sichtbaren Spalten übrig lassen.

## Tastenkürzel

| Taste | Aktion |
|-------|--------|
| G | Stundenzettel generieren |
| E | Excel-Export |
| P | PDF-Export |
| D | Ticket-Details anzeigen |
| M | Manuelle Zeit erfassen bzw. markierten Eintrag bearbeiten |
| ENTF | Markierten manuellen Eintrag löschen (mit Rückfrage) |
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
| Jira Host | URL der Jira-Instanz (Cloud: `…atlassian.net`) | — |
| Token | API-Token (Cloud) oder Bearer-Token (Data Center) | — |
| E-Mail | Atlassian-Login (Cloud) oder Jira-Benutzername (Data Center) | — |
| Jira-Modus (alte API) | Aus = Jira Cloud (v3), an = Data Center (v2) | aus |
| Budget-Custom-Field | Custom-Field-ID; Cloud unterstützt **Automatisch ermitteln** | customfield_36461 |
| Bundesland | Für Feiertagsberechnung | SN |
| Soll-Stunden/Tag | Arbeitsstunden pro Tag | 8.0 |
| Max. Jahresstunden | Obergrenze für Progressbar | 1720 |
| Urlaubstage | Für Jahres-Forecast | 30 |
| Stundensatz | Netto, nur TUI-Anzeige | 0 (aus) |
| MwSt-Satz | Prozent, für die Brutto-Berechnung | 19 |
| Jahr | Für Jahresansicht | aktuelles Jahr |
| Soll-Stunden im Export | Zeigt Soll-Zeile in Excel/PDF | false |
| Ticket-Links im Export | Hyperlinks in Excel/PDF | false |
| Standard-Kunde | Kunde für alle aus Jira geholten Einträge | Vertrieb |
| Kunden-Auswahl | Liste für das Kunden-Dropdown (kommagetrennt) | Vertrieb, Corporate |
| Manuelle Einträge markieren | Färbt manuelle Zeiten in Liste, Excel und PDF | true |
| Markierungsfarbe | `#RRGGBB`, `RRGGBB`, `#RGB` oder `255,0,0` | FF0000 |
| Spalten | Pro Spalte Anzeige, Export und Bezeichnung | alle aktiv |
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
