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

<p align="center">
  <img src="docs/images/teaser.png" width="70%" alt="jira-timesheet">
</p>

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
- **Meine Tickets** — Alle offenen Tickets, gruppiert danach, wer gerade am Zug ist: was du selbst bearbeitest, was auf Freigabe wartet, was im Backlog liegt, was zurückzugeben ist und was Jira für fertig hält, obwohl noch Arbeit bleibt. Mit Merkmalen wie "verwaist", "blockiert" oder "Pile of Shame" und einer Liegezeit in echten Arbeitstagen
- **Relevante Tickets** — Tickets, die dir nicht zugewiesen sind, dich aber betreffen: selbst angelegt, beobachtet, Zeit gebucht, bearbeitet oder namentlich erwähnt
- **Mein Team** — Derselbe Blick auf den Ticketstand von Kolleginnen und Kollegen, ohne dass diese etwas installieren müssen. Ohne Zeitbuchungen und ohne Auswertung: gezeigt wird, was das Jira-Board ohnehin jedem im Team zeigt
- **Auswertung** — Zulauf gegen Abgang je Monat und die Altersverteilung der offenen Tickets, als echte Diagramme mit Achsen direkt im Terminal (zuklappbar, über [textual-plotext](https://github.com/Textualize/textual-plotext))
- **Tab-Navigation** — Zwischen Ansichten wechseln mit TAB oder Klick
- **Jahresansicht** — 12 Monatskacheln mit Progressbar und Forecast (J)
- **Excel-Export** — Formatierter Stundenzettel mit Logo und Unterschriftszeile
- **PDF-Export** — Adobe-signierbar, Unicode-Schriftart (Arial)
- **Feiertage** — Deutsche Feiertage pro Bundesland, Lücken-Erkennung
- **Soll/Ist** — Arbeitszeitvergleich mit Differenz-Anzeige
- **MwSt konfigurierbar** — MwSt-Satz als Setting für die Netto/Brutto-Berechnung (Standard 19 %)
- **Ticket-Details** — Enter/D zeigt Status, Typ, Bearbeiter, Komponenten im Log
- **Ticket-Analyse** - Macht aus einem Ticket einen interaktiven Bericht: maßstabsgetreue Zeitachse des Lebenszyklus, Liegezeit je Status (Kalenderzeit gegen echte Arbeitszeit), Beteiligte, Kennzahlen wie Flow-Effizienz und erste Reaktion, dazu Befunde mit Beleg. Ergebnis ist eine einzelne HTML-Datei, die offline läuft (Taste `B`) Auffällig lange Liegezeiten werden rot markiert, verwandte Tickets zeigen ihren Titel, und der fertige Bericht öffnet sich gleich im Browser.
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

### Manuelle Installation (aus dem Quellcode)

Der Betrieb aus dem Quellcode braucht [uv](https://docs.astral.sh/uv/) - das
Werkzeug holt ein passendes Python und alle Abhängigkeiten. Einmalig
installieren:

**Windows (PowerShell):**
```powershell
irm https://astral.sh/uv/install.ps1 | iex
```

**Linux/macOS:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Danach das Terminal einmal schließen und neu öffnen, dann:

**Windows (PowerShell):**
```powershell
git clone https://github.com/michaelblaess/jira-timesheet.git
cd jira-timesheet
./bootstrap.ps1
./run.ps1
```

**Linux/macOS:**
```bash
git clone https://github.com/michaelblaess/jira-timesheet.git
cd jira-timesheet
./bootstrap.sh
./run.sh
```

`bootstrap` richtet die Umgebung einmalig ein, `run` startet das Programm - das
ist ab dann Dein einziger Befehl.

Dieser Weg funktioniert auch auf **Intel-Macs**: Die fertige Programmdatei wird
für Apple Silicon gebaut und startet dort mit `bad CPU type in executable` gar
nicht erst, während der Quellcode-Weg das Python passend zu Deinem Prozessor
zieht.

## Benutzung

```bash
jira-timesheet
```

### Haftungshinweis beim ersten Start

Beim ersten Start erscheint ein Hinweis, der bestätigt werden muss - ohne Zustimmung beendet sich das Programm. Grund: Das Werkzeug liest über die Jira-REST-API Arbeitszeit-Buchungen aus einem fremden System. Welche Vorgänge und Worklogs dabei sichtbar werden, bestimmen allein die Berechtigungen des verwendeten Zugangs, und je nach Rechtevergabe gehören dazu auch Buchungen anderer Personen. Mit der Bestätigung erklärst Du, das Programm nur gegen dazu berechtigte Jira-Instanzen einzusetzen und nur Daten auszuwerten, zu deren Verarbeitung Du befugt bist.

Die Zustimmung wird in `~/.jira-timesheet/disclaimer.json` festgehalten und nur erneut abgefragt, wenn sich der Wortlaut ändert. Den Speicherort zeigt der Reiter "Speicherort" im Einstellungsdialog - dort lässt sich die Datei auch löschen, um den Hinweis wieder anzuzeigen.

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

### Ticket-Ansichten einrichten

Die Reiter **Meine Tickets**, **Relevante Tickets** und **Mein Team** gruppieren die
Tickets danach, wer gerade am Zug ist. Welcher Status zu welcher Gruppe gehört,
weiß nur deine Jira-Instanz - jeder Workflow heißt anders. Deshalb trägst du die
Zuordnung einmalig im Settings-Tab **Tickets** ein, je Gruppe eine Kommaliste.

| Gruppe | Was gehört hinein | Beispiel |
|--------|-------------------|----------|
| Ich bin dran | Status, in denen du selbst arbeitest | `In Bearbeitung, Im Review` |
| Backlog | Bereit zum Ziehen, noch nicht begonnen | `Bereit, Eingeplant` |
| Andere sind dran | Wartet auf Freigabe durch jemand anderen | `Wartet auf Freigabe` |
| Rückläufer | Ausgeliefert, zur Bewertung beim Autor | `Ausgeliefert` |
| Abschluss offen | Von Jira als fertig gezählt, mit Restarbeit | `Zur Abnahme, Doku offen` |

### Mein Team einrichten

Im Settings-Tab **Mein Team** hinterlegst du die Kolleginnen und Kollegen, deren
Ticketstand du sehen willst. Gesucht wird über den **Namen**, nicht über die
Mailadresse - und das hat einen handfesten Grund:

- Ein Jira-Konto gibt seine Mailadresse nur heraus, wenn das Profil es zulässt.
  In einer vermessenen Instanz war sie bei jeder vierten Person unsichtbar.
- Ein Mensch kann mehrere Konten führen. Welches davon die Arbeit trägt, lässt
  sich aus der Adresse nicht ablesen: mal ist es das mit Adresse, mal das ohne.

Die Trefferliste zeigt deshalb neben Name und Adresse die Zahl der offenen
Tickets und den Zeitpunkt der **jüngsten Änderung**, sortiert nach Aktualität.
Bei mehreren Konten ist das aktuelle nicht zwingend das größte - genau
deswegen steht die Spalte da.

Ein Treffer wird entweder als neue Person übernommen oder einer vorhandenen als
weiteres Konto zugeordnet. Der Anzeigename ist frei wählbar und überschreibt den
aus Jira, das ist bei drei verschiedenen Schreibweisen derselben Person hilfreich.

**Was die Ansicht bewusst nicht zeigt:** keine Zeitbuchungen, keinen "Pile of
Shame", keine Auswertung. Das Jira-Board zeigt jedem im Team die Tickets der
anderen, aber weder Buchungen noch Durchsatz - daran hält sich diese Ansicht.
Sie ist eine schnellere Linse auf das, was im Board ohnehin steht, und kein
Werkzeug zur Leistungsmessung.

**"Abschluss offen" ist das wichtigste Feld.** Jira sortiert diese Status in die
Kategorie *Fertig* ein - eine Abfrage über `statusCategory != Done` findet sie
also nicht, und sie tauchen in keiner Liste auf. Bei einer vermessenen Instanz
waren das 24 von 93 zugewiesenen Tickets, die lautlos fehlten. Nur wenn du sie
hier einträgst, holt die Anwendung sie mit einer zweiten Abfrage dazu.

Was du nicht einträgst, ordnet Jira selbst grob nach seiner Statuskategorie zu.
Das funktioniert sofort, ist aber deutlich gröber - Rückläufer und wartende
Freigaben lassen sich so nicht auseinanderhalten.

Die Spalte **Merkmale** zeigt, warum ein Ticket auffällt:

| Merkmal | Bedeutung |
|---------|-----------|
| Pile of Shame | Der Status behauptet Aktivität, aber seit der Schwelle gab es weder eine Änderung noch eine gebuchte Stunde |
| verwaist | Seit sehr langer Zeit unverändert (Vorgabe: 180 Tage) |
| Priorität | Prioritätsstufe in der oberen Gruppe deiner Rangfolge |
| nachhaken | Wartet auf Freigabe durch jemand anderen |
| Rückgabe | Ausgeliefert, fremder Autor - gehört zurückgegeben, nicht bearbeitet |
| blockiert | Ein Vorgänger ist noch offen |

Die **Liegezeit (AT)** rechnet in Arbeitstagen, Montag bis Freitag zwischen 8 und
18 Uhr. Ein Ticket, das Freitagnachmittag liegen bleibt und Montagvormittag
wieder angefasst wird, hat einen Arbeitstag gelegen und nicht drei. Feiertage
kennt die Rechnung nicht.

Die drei **Schwellen** bestimmen, ab wann ein Ticket den Pile-of-Shame-Marker
bekommt - je Gruppe getrennt, weil ein liegendes Backlog-Ticket normal ist und
ein liegendes Ticket in Arbeit nicht. `0` schaltet die Prüfung für eine Gruppe
ab. Die Vorgabewerte sind Setzungen aus der Praxis, keine Messungen: wenn deine
Tickets üblicherweise länger liegen, dreh sie hoch, statt die Marker zu ignorieren.

Beide Ansichten laden beim ersten Ansehen und danach nur noch auf `F5` - ein
Abruf über alle Tickets kostet je nach Instanz eine Minute. Die **Auswertung**
unter der Tabelle ist zugeklappt und holt ihre Zahlen erst beim Aufklappen: sie
braucht eine eigene Abfrage über die gesamte Historie. Sie zeigt Zulauf gegen
Abgang je Monat und die Altersverteilung der offenen Tickets, dazu eine Zeile
mit Bestand, Durchsatz und Saldo. Den kumulierten Bestandsverlauf zeigt nur die
Qt-Fassung - im Terminal reicht die Breite nicht für ein drittes Diagramm.

## Tastenkürzel

| Taste | Aktion |
|-------|--------|
| G | Stundenzettel generieren |
| E | Excel-Export |
| P | PDF-Export |
| D | Ticket-Details anzeigen |
| B | Ticket-Analyse (interaktiver Bericht als HTML-Datei) |
| M | Manuelle Zeit erfassen bzw. markierten Eintrag bearbeiten |
| ENTF | Markierten manuellen Eintrag löschen (mit Rückfrage) |
| TAB | Tab wechseln (Liste / Kalender / Meine Tickets / Relevante Tickets / Mein Team) |
| F5 | Ticket-Ansicht des aktuellen Reiters neu laden |
| / | Suchfeld des aktuellen Reiters fokussieren |
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
| Budget-Custom-Field | Custom-Field-ID; Cloud unterstützt **Automatisch ermitteln** | (leer) |
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
| Ich bin dran | Status, in denen du selbst arbeitest | (leer) |
| Backlog | Status "bereit zum Ziehen" | (leer) |
| Andere sind dran | Status, die auf fremde Freigabe warten | (leer) |
| Rückläufer | Status "ausgeliefert, zur Bewertung beim Autor" | (leer) |
| Abschluss offen | Status, die Jira als fertig zählt, obwohl Arbeit bleibt | (leer) |
| Prioritäten | Rangfolge der Prioritätsstufen, dringendstes zuerst | (eingebaut) |
| Zeitfenster | Tage, die "Relevante Tickets" zurückblickt (0 = alle) | 90 |
| Verwaist ab | Tage ohne Änderung bis zur Markierung "verwaist" | 180 |
| Schwelle aktiv | Arbeitstage ohne Regung in "Ich bin dran" (0 = aus) | 20 |
| Schwelle Freigabe | Arbeitstage ohne Regung in "Andere sind dran" (0 = aus) | 10 |
| Schwelle Abschluss | Arbeitstage ohne Regung in "Abschluss offen" (0 = aus) | 0 |

## Tech Stack

- [Python](https://python.org) >= 3.12
- [Textual](https://textual.textualize.io) — TUI Framework
- [Rich](https://rich.readthedocs.io) — Terminal Formatting
- [httpx](https://www.python-httpx.org) — Async HTTP Client
- [openpyxl](https://openpyxl.readthedocs.io) — Excel Export
- [fpdf2](https://py-pdf.github.io/fpdf2) — PDF Export
- [holidays](https://python-holidays.readthedocs.io) — Feiertagsberechnung

## Wenn etwas schiefgeht

Stuerzt das Programm ab, landet der Bericht auf Platte statt nur im Terminal -
zwei Dateien neben den Einstellungen, beide im Speicherort-Tab der
Einstellungen verlinkt, sobald es sie gibt:

| Datei | Wofuer |
| --- | --- |
| `last-crash.txt` | Python-Fehler samt Traceback. Wird geschrieben, **bevor** der Fehlerdialog laeuft - faellt dieser beim Neuaufbau selbst mit, waere der Bericht sonst verloren. |
| `fault.log` | Alles darunter: native Speicherzugriffsfehler, Stack-Overflow, fataler Interpreter-Fehler. Solche Abstuerze laufen an Pythons Fehlerbehandlung vorbei. |

Beide Dateien werden **angehaengt**, nicht ersetzt - ein zweiter Absturz
verdeckt den ersten nicht.

`fault.log` bekommt ausserdem je Programmlauf eine Start- und eine Endzeile.
Damit ist ablesbar, was passiert ist:

| Was in der Datei steht | Was es bedeutet |
| --- | --- |
| Start, Traceback, Ende | Python-Fehler, das Programm hat ihn gesehen |
| Start, Ende | sauber beendet |
| Start, dann nichts | Prozess hart abgeraeumt - **kein** Python-Fehler |

Ein hart abgeraeumter Prozess und ein Absturz sehen im Terminal gleich aus.
Erst die fehlende Endzeile trennt beide Faelle.

Unter Windows startest Du das Programm am besten ueber `run.ps1`: das Skript
setzt das Terminal auch dann wieder zurueck, wenn das Programm hart abstuerzt
und selbst nichts mehr tun kann. Sonst bleibt die Maus-Erfassung aktiv, und
jede Mausbewegung kippt Steuerzeichen in die Eingabezeile.

### Wenn die Oberfläche nicht mehr reagiert

Ein Hänger hinterlässt keinen Absturzbericht - es ist ja nichts abgestürzt.
Öffne ein **zweites** Terminalfenster (macOS: Cmd+N) und hole dort den Beleg:

**macOS:**
```bash
pgrep -fl jira_timesheet
top -l 2 -pid $(pgrep -f jira_timesheet | head -1) | grep -E "^PID|python"
```

**Linux:**
```bash
pgrep -fl jira_timesheet
top -b -n 2 -p $(pgrep -f jira_timesheet | head -1) | grep -E "^ *PID|python"
```

**Windows (PowerShell, zweites Fenster):**
```powershell
$p = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*jira_timesheet*' }
Get-Process -Id $p.ProcessId | Select-Object Id, CPU
Start-Sleep 3
Get-Process -Id $p.ProcessId | Select-Object Id, CPU
```

`CPU` zählt Prozessorsekunden. Bleibt der Wert zwischen beiden Abfragen gleich,
wartet das Programm. Steigt er, dreht es sich im Kreis. Beenden lässt es sich
mit `Stop-Process -Id $p.ProcessId -Force`.

Die CPU-Spalte trennt die Fälle:

| Befund | Bedeutung |
| --- | --- |
| CPU nahe 0 %, Zustand `S` | wartet auf eine Antwort aus dem Netz - langsame oder abgerissene Verbindung |
| CPU nahe 100 %, Zustand `R` | Endlosschleife - bitte mit den letzten Protokollzeilen melden |
| Zustand `U` (macOS) / `D` (Linux) | hängt im Dateizugriff und lässt sich nicht beenden. Meist sind synchronisierte Ordner (Dropbox, iCloud Drive) die Ursache - das Arbeitsverzeichnis gehört dort nicht hinein |

Aus dem Hänger kommst Du mit `kill <PID>` aus dem zweiten Fenster oder über
"Sofort beenden" im Apfel-Menü. Es geht nichts verloren, die Einstellungen
werden bei jeder Änderung geschrieben.

## Lizenz

Apache License 2.0

---

> **Trademark Notice:** "Jira" is a registered trademark of [Atlassian Corporation](https://www.atlassian.com/). This project is not affiliated with, endorsed by, or sponsored by Atlassian.
