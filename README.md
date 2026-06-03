# Jira Timesheet

<p align="center">
  <img src="docs/flags/gb.svg" height="13" alt=""> <b>English</b> ·
  <img src="docs/flags/de.svg" height="13" alt=""> <a href="README.de.md">Deutsch</a>
</p>

---

[![Stars](https://img.shields.io/github/stars/michaelblaess/jira-timesheet?logo=github&logoColor=white&color=fbbf24)](https://github.com/michaelblaess/jira-timesheet/stargazers)
[![Forks](https://img.shields.io/github/forks/michaelblaess/jira-timesheet?logo=github&logoColor=white&color=34d399)](https://github.com/michaelblaess/jira-timesheet/network/members)
[![Issues](https://img.shields.io/github/issues/michaelblaess/jira-timesheet?logo=github&logoColor=white&color=f87171)](https://github.com/michaelblaess/jira-timesheet/issues)
[![Pull Requests](https://img.shields.io/github/issues-pr/michaelblaess/jira-timesheet?logo=github&logoColor=white&color=a78bfa)](https://github.com/michaelblaess/jira-timesheet/pulls)

[![Last Commit](https://img.shields.io/github/last-commit/michaelblaess/jira-timesheet?logo=git&logoColor=white&color=3b82f6)](https://github.com/michaelblaess/jira-timesheet/commits/main)
[![License](https://img.shields.io/badge/license-Apache_2.0-3b82f6)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12+-3b82f6?logo=python&logoColor=white)](https://www.python.org/)

Terminal-based application (TUI) for generating timesheets from Jira worklogs.

> **Disclaimer:** This project is **not** developed, supported, or authorized by Atlassian. "Jira" and "Atlassian" are registered trademarks of [Atlassian Corporation](https://www.atlassian.com/). This tool uses the public Jira REST API and is not affiliated with Atlassian.

## Screenshots

The interface ships with retro themes. Every view is shown below across a range of them.

### List view

<p align="center">
  <img src="docs/screenshots/01-main-beastie.png" width="32%" alt="List view (Beastie)">
  <img src="docs/screenshots/01-main-bebox.png" width="32%" alt="List view (BeBox)">
  <img src="docs/screenshots/01-main-classic-terminal.png" width="32%" alt="List view (Classic Terminal)">
  <img src="docs/screenshots/01-main-corleone.png" width="32%" alt="List view (Corleone)">
  <img src="docs/screenshots/01-main-gemstone.png" width="32%" alt="List view (Gemstone)">
  <img src="docs/screenshots/01-main-metropolis.png" width="32%" alt="List view (Metropolis)">
  <img src="docs/screenshots/01-main-miami.png" width="32%" alt="List view (Miami)">
</p>

### Calendar view

<p align="center">
  <img src="docs/screenshots/02-month-view-beastie.png" width="32%" alt="Calendar view (Beastie)">
  <img src="docs/screenshots/02-month-view-bebox.png" width="32%" alt="Calendar view (BeBox)">
  <img src="docs/screenshots/02-month-view-classic-terminal.png" width="32%" alt="Calendar view (Classic Terminal)">
  <img src="docs/screenshots/02-month-view-corleone.png" width="32%" alt="Calendar view (Corleone)">
  <img src="docs/screenshots/02-month-view-gemstone.png" width="32%" alt="Calendar view (Gemstone)">
  <img src="docs/screenshots/02-month-view-metropolis.png" width="32%" alt="Calendar view (Metropolis)">
  <img src="docs/screenshots/02-month-view-miami.png" width="32%" alt="Calendar view (Miami)">
</p>

### Year view with forecast

<p align="center">
  <img src="docs/screenshots/03-year-view-beastie.png" width="32%" alt="Year view (Beastie)">
  <img src="docs/screenshots/03-year-view-bebox.png" width="32%" alt="Year view (BeBox)">
  <img src="docs/screenshots/03-year-view-classic-terminal.png" width="32%" alt="Year view (Classic Terminal)">
  <img src="docs/screenshots/03-year-view-corleone.png" width="32%" alt="Year view (Corleone)">
  <img src="docs/screenshots/03-year-view-gemstone.png" width="32%" alt="Year view (Gemstone)">
  <img src="docs/screenshots/03-year-view-metropolis.png" width="32%" alt="Year view (Metropolis)">
  <img src="docs/screenshots/03-year-view-miami.png" width="32%" alt="Year view (Miami)">
</p>

### Ticket details

<p align="center">
  <img src="docs/screenshots/04-details-beastie.png" width="32%" alt="Ticket details (Beastie)">
  <img src="docs/screenshots/04-details-bebox.png" width="32%" alt="Ticket details (BeBox)">
  <img src="docs/screenshots/04-details-classic-terminal.png" width="32%" alt="Ticket details (Classic Terminal)">
  <img src="docs/screenshots/04-details-metropolis.png" width="32%" alt="Ticket details (Metropolis)">
</p>

### Settings

<p align="center">
  <img src="docs/screenshots/05-settings-beastie.png" width="32%" alt="Settings - language (Beastie)">
  <img src="docs/screenshots/05-settings-classic-terminal.png" width="32%" alt="Settings - language (Classic Terminal)">
  <img src="docs/screenshots/05-settings-corleone.png" width="32%" alt="Settings - language (Corleone)">
  <img src="docs/screenshots/05-settings-gemstone-1.png" width="32%" alt="Settings - language (Gemstone)">
  <img src="docs/screenshots/05-settings-gemstone-2.png" width="32%" alt="Settings - calculation (Gemstone)">
  <img src="docs/screenshots/05-settings-metropolis.png" width="32%" alt="Settings - calculation (Metropolis)">
  <img src="docs/screenshots/05-settings-metropolis-02.png" width="32%" alt="Settings - export (Metropolis)">
  <img src="docs/screenshots/05-settings-metropolis-03.png" width="32%" alt="Settings - Jira (Metropolis)">
</p>

### Info

<p align="center">
  <img src="docs/screenshots/06-info-beastie.png" width="32%" alt="Info dialog (Beastie)">
  <img src="docs/screenshots/06-info-bebox.png" width="32%" alt="Info dialog (BeBox)">
  <img src="docs/screenshots/06-info-metropolis.png" width="32%" alt="Info dialog (Metropolis)">
</p>

## Features

- **Jira integration** — Fetch worklogs via REST API (Bearer token auth)
- **List view** — Tabular with calendar week, weekday, day groups, target/actual hours
- **Search / filter** — Live filter by ticket ID or description (`/` to focus, history with dropdown)
- **Calendar view** — Monthly calendar with color-coded day tiles
- **Tab navigation** — Switch between views with TAB or click
- **Year view** — 12 monthly tiles with progress bar and forecast (J)
- **Excel export** — Formatted timesheet with logo and signature line
- **PDF export** — Adobe-signable, Unicode font (Arial)
- **Public holidays** — German public holidays per federal state, gap detection
- **Target/actual** — Working time comparison with difference display
- **Ticket details** — Enter/D shows status, type, assignee, components in the log
- **Anonymization** — Anonymize data with a keypress for safe screenshots
- **Worklog cache** — Completed months cached, year view loads instantly
- **Bilingual UI** — German/English, switchable via `--lang` or the settings dialog
- **31 retro themes** — via theme picker (Ctrl+P), see [textual-themes](https://github.com/michaelblaess/textual-themes)

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

Afterwards just type `jira-timesheet` in the terminal.

### Manual Installation

```bash
git clone https://github.com/michaelblaess/jira-timesheet.git
cd jira-timesheet
setup.bat
run.bat
```

## Usage

```bash
jira-timesheet
```

The interface language (German/English) follows the `--lang` flag — the choice is saved and can also be changed in the settings dialog:

```bash
jira-timesheet --lang en
```

On first start, press `S` for settings and configure:
- Jira host URL
- Bearer token
- Email (Jira username)
- Federal state (public holidays)

Then `G` to generate the timesheet.

## Keyboard Shortcuts

| Key | Action |
|-------|--------|
| G | Generate timesheet |
| E | Excel export |
| P | PDF export |
| D | Show ticket details |
| TAB | Switch tab (list / calendar) |
| / | Focus search field (list view) |
| R | Reset cache |
| J | Year view with forecast |
| A | Anonymize data |
| < / > | Switch month |
| S | Settings |
| I | Info |
| C | Copy log |
| L | Show/hide log |
| Ctrl+P | Switch theme |
| Q | Quit |

## Configuration

Settings are stored in `~/.jira-timesheet/settings.json`:

| Setting | Description | Default |
|-------------|-------------|---------|
| Jira host | URL of the Jira instance | — |
| Token | Bearer token for authentication | — |
| Email | Jira username | — |
| Federal state | For public holiday calculation | SN |
| Target hours/day | Working hours per day | 8.0 |
| Max. yearly hours | Upper limit for progress bar | 1720 |
| Vacation days | For yearly forecast | 30 |
| Hourly rate | Net, TUI display only | 0 (off) |
| Year | For year view | current year |
| Target hours in export | Shows target row in Excel/PDF | false |
| Ticket links in export | Hyperlinks in Excel/PDF | false |
| Language | UI language (de / en) | de |

## Tech Stack

- [Python](https://python.org) >= 3.12
- [Textual](https://textual.textualize.io) — TUI framework
- [Rich](https://rich.readthedocs.io) — Terminal formatting
- [httpx](https://www.python-httpx.org) — Async HTTP client
- [openpyxl](https://openpyxl.readthedocs.io) — Excel export
- [fpdf2](https://py-pdf.github.io/fpdf2) — PDF export
- [holidays](https://python-holidays.readthedocs.io) — Public holiday calculation

## License

Apache License 2.0

---

> **Trademark Notice:** "Jira" is a registered trademark of [Atlassian Corporation](https://www.atlassian.com/). This project is not affiliated with, endorsed by, or sponsored by Atlassian.
