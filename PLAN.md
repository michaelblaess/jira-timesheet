# Jira Timesheet — Backlog / Ideen

## Monatswechsel

- Monat mit Pfeiltasten wechseln (◄ / ►) funktioniert bereits im Code
- Pruefen ob das auch in der TUI korrekt funktioniert und Daten neu geladen werden

## Info-Dialog

- Anderes Zitat von Martin Luther King waehlen

## Wochentag und Kalenderwoche

- In der Tabelle den Wochentag mit anzeigen (Mo, Di, Mi, ...)
- Kalenderwoche als Gruppierung oder Spalte ergaenzen
- Auch im Excel/PDF Export beruecksichtigen

## Unter 8h pro Tag hervorheben

- Wenn Tagessumme < 8h: Zeile leicht rot/rosa einfaerben
- Schwellenwert ggf. konfigurierbar in Settings (default: 8h)

## Luecken-Erkennung (fehlende Arbeitstage)

- Wenn innerhalb einer Woche Tage fehlen (z.B. Mo, Di, Do, Fr aber kein Mi):
  - Den fehlenden Tag als leere Zeile mit Hinweis einfuegen
  - Visuell hervorheben (z.B. grau hinterlegt, "— kein Eintrag —")
- Wochenenden und Feiertage dabei ignorieren

## Kalenderansicht / Kachelansicht

- Mit TAB zwischen Tabellenansicht und Kalenderansicht wechseln
- Kalenderansicht: Monatskalender als Kacheln / Grid
  - Jeder Tag als Kachel mit Stundenanzahl
  - Farbcodierung: gruen (>= 8h), gelb (< 8h), rot (0h / Luecke), grau (Wochenende/Feiertag)
- Gut fuer schnellen visuellen Ueberblick

## Feiertagskalender

- Deutsche Feiertage (bundeslandabhaengig) integrieren
- Bibliothek: `holidays` (pip install holidays) oder eigene Berechnung
- Feiertage in der Tabelle markieren und bei Luecken-Erkennung beruecksichtigen
- Feiertage zaehlen nicht als fehlende Arbeitstage

## Bundesland in Settings

- Neues Feld `federal_state` in Settings (z.B. "SN" fuer Sachsen, "TH" fuer Thueringen)
- Wird fuer Feiertagsberechnung benoetigt
- Default: "SN" (Sachsen — enviaM-Gebiet)

## Soll-Arbeitszeitstunden

- Pro Woche: 5 Arbeitstage minus Feiertage = Soll-Tage * 8h
- Pro Monat: alle Arbeitstage minus Feiertage = Soll-Tage * 8h
- In der Zusammenfassung anzeigen:
  - "Soll: 168.00h | Ist: 142.50h | Differenz: -25.50h"
- Auch im Excel/PDF Export als zusaetzliche Zeile

## Umlaute korrigieren

- PDF-Export: Helvetica unterstuetzt keine Umlaute (ae, oe, ue, ss)
- Loesung: Unicode-Font einbetten (z.B. DejaVu Sans) oder Umlaute ersetzen
- Auch im Excel-Export pruefen ob Umlaute korrekt dargestellt werden
