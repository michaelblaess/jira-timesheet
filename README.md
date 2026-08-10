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

Terminal-based application (TUI) for timesheets from Jira worklogs — including manual time entry for hours that are not booked in Jira.

<p align="center">
  <img src="docs/images/teaser.png" width="70%" alt="jira-timesheet">
</p>

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

- **Jira Cloud & Data Center** — Worklogs via REST API; Jira Cloud (v3, basic auth with API token) by default, with a toggle for legacy Jira Server/Data Center (v2, bearer token)
- **Budget field auto-detect** — Find the budget custom field automatically on Jira Cloud (no manual ID lookup)
- **List view** — Tabular with calendar week, weekday, day groups, target/actual hours
- **Search / filter** — Live filter by ticket ID or description (`/` to focus, history with dropdown)
- **Resizable columns** — Drag the divider in the column header; double-click resets it, widths are persisted. Otherwise the description column fills the remaining width automatically
- **Manual time tracking** — Record time that is not booked in Jira via a dialog (`m`), edit and delete it (`DEL`); stored in SQLite, colour-marked in the list, Excel and PDF
- **Configurable export columns** — Every column can be toggled and renamed (settings tab "Columns"), including a customer column
- **Calendar view** — Monthly calendar with color-coded day tiles
- **My tickets** — All open tickets, grouped by whose turn it is: what you are working on, what waits for approval, what sits in the backlog, what should be handed back, and what Jira counts as done although work remains. With flags such as "stale", "blocked" or "pile of shame" and an idle time counted in real working days
- **Relevant tickets** — Tickets not assigned to you that still concern you: reported, watched, worked on, updated or mentioned by name
- **My team** — The same view on a colleague's tickets, without them having to install anything. No worklogs and no analysis: it shows what the Jira board shows everyone on the team anyway
- **Analysis** — Inflow versus outflow per month and the age distribution of open tickets, drawn as real charts with axes right in the terminal (collapsible, via [textual-plotext](https://github.com/Textualize/textual-plotext))
- **Tab navigation** — Switch between views with TAB or click
- **Year view** — 12 monthly tiles with progress bar and forecast (J)
- **Excel export** — Formatted timesheet with logo and signature line
- **PDF export** — Adobe-signable, Unicode font (Arial)
- **Public holidays** — German public holidays per federal state, gap detection
- **Target/actual** — Working time comparison with difference display
- **Configurable VAT** — VAT rate as a setting for the net/gross calculation (default 19%)
- **Ticket details** — Enter/D shows status, type, assignee, components in the log
- **Ticket analysis** - Turns any ticket into an interactive report: a true-to-scale timeline of its life cycle, waiting time per status (calendar time versus actual working hours), the people involved, key figures such as flow efficiency and first response, plus findings with evidence. The result is a single HTML file that works offline (key `B`) Unusually long waiting times are marked in red, related tickets show their title, and the finished report opens straight in the browser.
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

### Manual Installation (from source)

Running from source needs [uv](https://docs.astral.sh/uv/) - it fetches a
matching Python and every dependency. Install it once:

**Windows (PowerShell):**
```powershell
irm https://astral.sh/uv/install.ps1 | iex
```

**Linux/macOS:**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Close and reopen the terminal afterwards, then:

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

`bootstrap` sets up the environment once, `run` starts the program - that is
the command you use from then on.

This route also works on **Intel Macs**: the released binary is built for Apple
Silicon and refuses to start there with `bad CPU type in executable`, while the
source build picks the Python matching your processor.

## Usage

```bash
jira-timesheet
```

### Liability notice on first start

On its first start the program shows a notice that has to be confirmed - without your consent it exits. The reason: this tool reads work log entries from a third-party system through the Jira REST API. Which issues and work logs become visible is determined solely by the permissions of the account you use, and depending on how rights are assigned these may include entries booked by other people. By confirming, you declare that you will only use the program against Jira instances you are authorised to access, and that you will only evaluate data you are permitted to process.

Your consent is recorded in `~/.jira-timesheet/disclaimer.json` and is only requested again when the wording changes. The "Storage" tab of the settings dialog shows the location, where you can also delete the file to see the notice again.

The interface language (German/English) follows the `--lang` flag — the choice is saved and can also be changed in the settings dialog:

```bash
jira-timesheet --lang en
```

On first start, press `S` for settings and configure:
- Jira host URL (Cloud: the canonical `https://your-company.atlassian.net`)
- Token — Jira Cloud: an API token from [id.atlassian.com](https://id.atlassian.com/manage-profile/security/api-tokens); Data Center: a bearer token (PAT)
- Email / login — Cloud: your Atlassian login email; Data Center: your Jira username
- **Jira mode** — leave off for Jira Cloud, enable for a legacy Server/Data Center
- Budget custom field — on Cloud use **Auto-detect** to fill it in automatically
- Federal state (public holidays)

Then `G` to generate the timesheet.

### Recording time that is not in Jira

Not every hour ends up as a worklog in Jira. `M` opens a dialog for date,
ticket, description, customer and effort. The effort may be written the way you
note it anyway: `3h 30m`, `3:30`, `3.5` or `45m`.

These entries live in their own SQLite file
(`~/.jira-timesheet/manual-entries.db`) and **never** in the Jira cache. They
count everywhere — daily total, monthly total, target/actual, calendar, year
view, Excel and PDF — and are colour-marked so it is obvious at a glance what
comes from Jira and what does not. How much of it was entered manually is shown
in the stats line, in every month tile of the year view and in its yearly total.

With the cursor on a manual entry, `M` opens it for editing and `DEL` deletes it
after a confirmation. The edit dialog also has a **Delete** button that asks the
same question.

A **right-click** on a row opens a context menu: show details, open the ticket in
the browser, record time for that day, edit or delete the entry. Whatever does
not apply to the clicked row is greyed out, so the items always sit in the same
place. It also works on a gap row (`— no entry —`) to fill in time right there.

### Adjusting export columns

In the settings tab **Columns** each of the eight columns (week, day, date,
ticket, description, customer, effort, daily total) has two checkboxes:
**Display** controls the list view, **Export** the Excel and PDF file. Both are
switched independently — a column can go into the export without cluttering the
list.

The text field next to them is the heading **in the export**; the list keeps its
translated headings so it follows a language change. The description is the
flexible column: it takes whatever width the other visible columns leave.

### Setting up the ticket views

The tabs **My tickets**, **Relevant tickets** and **My team** group the tickets by whose
turn it is. Which status belongs to which group is something only your Jira
instance knows - every workflow uses different names. You therefore enter the
mapping once in the settings tab **Tickets**, one comma-separated list per group.

| Group | What belongs there | Example |
|-------|--------------------|---------|
| My turn | Status values you are actively working in | `In progress, In review` |
| Backlog | Ready to pull, not started yet | `Ready, Scheduled` |
| Someone else's turn | Waiting for approval by someone else | `Awaiting approval` |
| Hand back | Delivered, waiting for the reporter's assessment | `Delivered` |
| Closing open | Counted as done by Jira, work remains | `For acceptance, Docs open` |

### Setting up My team

In the settings tab **My team** you add the colleagues whose ticket status you
want to see. Search by **name**, not by email address - and there is a solid
reason for that:

- A Jira account only reveals its email address if the profile allows it. In one
  measured instance it was invisible for every fourth person.
- One person may run several accounts. Which one carries the work cannot be
  derived from the address: sometimes it is the one with an address, sometimes
  the one without.

The hit list therefore shows, next to name and address, the number of open
tickets and the timestamp of the **most recent change**, sorted by recency. With
several accounts the current one is not necessarily the largest - which is
exactly why that column is there.

A hit is either added as a new person or attached to an existing one as a further
account. The display name is free to choose and overrides the one from Jira,
which helps when the same person appears under three different spellings.

**What the view deliberately does not show:** no worklogs, no "pile of shame",
no analysis. The Jira board shows everyone on the team the tickets of the others,
but neither bookings nor throughput - and this view sticks to that. It is a
faster lens on what the board already holds, not a productivity tool.

**"Closing open" is the most important field.** Jira files these status values
under the *Done* category - a query on `statusCategory != Done` will not find
them, and they show up in no list at all. On one measured instance that was 24
out of 93 assigned tickets, missing silently. Only if you enter them here does
the application fetch them with a second query.

Anything you leave out is mapped roughly by Jira itself, using its status
category. That works right away but is much coarser - hand-backs and pending
approvals cannot be told apart that way.

The **Flags** column shows why a ticket stands out:

| Flag | Meaning |
|------|---------|
| Pile of shame | The status claims activity, but since the threshold there was neither a change nor a logged hour |
| stale | Unchanged for a very long time (default: 180 days) |
| priority | Priority level in the upper group of your order |
| follow up | Waiting for approval by someone else |
| hand back | Delivered, foreign reporter - return it instead of working on it |
| blocked | A predecessor is still open |

**Idle (WD)** counts working days, Monday to Friday between 8 am and 6 pm. A
ticket left on Friday afternoon and picked up on Monday morning has been idle
for one working day, not three. Public holidays are not taken into account.

The three **thresholds** decide when a ticket earns the pile-of-shame flag -
separately per group, because a backlog ticket sitting still is normal while a
ticket in progress sitting still is not. `0` disables the check for a group. The
defaults are settings taken from practice, not measurements: if your tickets
usually rest longer, raise them instead of ignoring the flags.

Both views load when first opened and after that only on `F5` - a query across
all tickets takes about a minute depending on the instance. The **Analysis**
below the table starts collapsed and only fetches its numbers when opened: it
needs a query of its own across the entire history. It shows inflow versus
outflow per month and the age distribution of open tickets, plus a line with
backlog, throughput and balance. The cumulative backlog curve exists only in the
Qt edition - the terminal is not wide enough for a third chart.

## Keyboard Shortcuts

| Key | Action |
|-------|--------|
| G | Generate timesheet |
| E | Excel export |
| P | PDF export |
| D | Show ticket details |
| B | Ticket analysis (interactive report as an HTML file) |
| M | Record manual time, or edit the selected entry |
| DEL | Delete the selected manual entry (with confirmation) |
| TAB | Switch tab (list / calendar / my tickets / relevant tickets) |
| F5 | Reload the ticket view of the current tab |
| / | Focus the search field of the current tab |
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
| Jira host | URL of the Jira instance (Cloud: `…atlassian.net`) | — |
| Token | API token (Cloud) or bearer token (Data Center) | — |
| Email | Atlassian login (Cloud) or Jira username (Data Center) | — |
| Jira mode (legacy API) | Off = Jira Cloud (v3), on = Data Center (v2) | off |
| Budget custom field | Custom field ID; Cloud supports **Auto-detect** | (leer) |
| Federal state | For public holiday calculation | SN |
| Target hours/day | Working hours per day | 8.0 |
| Max. yearly hours | Upper limit for progress bar | 1720 |
| Vacation days | For yearly forecast | 30 |
| Hourly rate | Net, TUI display only | 0 (off) |
| VAT rate | Percent, for the gross calculation | 19 |
| Year | For year view | current year |
| Target hours in export | Shows target row in Excel/PDF | false |
| Ticket links in export | Hyperlinks in Excel/PDF | false |
| Default customer | Customer for all entries fetched from Jira | Vertrieb |
| Customer choices | List for the customer dropdown (comma-separated) | Vertrieb, Corporate |
| Highlight manual entries | Colours manual time in list, Excel and PDF | true |
| Highlight colour | `#RRGGBB`, `RRGGBB`, `#RGB` or `255,0,0` | FF0000 |
| Columns | Per column display, export and label | all enabled |
| Language | UI language (de / en) | de |
| My turn | Status values you are actively working in | (empty) |
| Backlog | Status values ready to pull | (empty) |
| Someone else's turn | Status values waiting for external approval | (empty) |
| Hand back | Status "delivered, waiting for the reporter" | (empty) |
| Closing open | Status Jira counts as done although work remains | (empty) |
| Priorities | Order of priority levels, most urgent first | (built-in) |
| Time window | Days that "relevant tickets" looks back (0 = all) | 90 |
| Stale after | Days without a change until the "stale" flag | 180 |
| Threshold active | Working days without motion in "my turn" (0 = off) | 20 |
| Threshold approval | Working days without motion in "someone else's turn" (0 = off) | 10 |
| Threshold closing | Working days without motion in "closing open" (0 = off) | 0 |

## Tech Stack

- [Python](https://python.org) >= 3.12
- [Textual](https://textual.textualize.io) — TUI framework
- [Rich](https://rich.readthedocs.io) — Terminal formatting
- [httpx](https://www.python-httpx.org) — Async HTTP client
- [openpyxl](https://openpyxl.readthedocs.io) — Excel export
- [fpdf2](https://py-pdf.github.io/fpdf2) — PDF export
- [holidays](https://python-holidays.readthedocs.io) — Public holiday calculation

## When something goes wrong

If the program crashes, the report is written to disk instead of only to the
terminal - two files next to the settings, both linked from the storage tab in
the settings once they exist:

| File | What for |
| --- | --- |
| `last-crash.txt` | Python errors including the traceback. Written **before** the error dialog runs - if that dialog dies during its own re-layout, the report would otherwise be lost. |
| `fault.log` | Everything below that: native access violations, stack overflow, fatal interpreter errors. Such crashes bypass Python's error handling entirely. |

Both files are **appended to**, not replaced - a second crash does not hide the
first one.

`fault.log` also gets a start and an end line per run, which makes the file
readable at a glance:

| What the file contains | What it means |
| --- | --- |
| start, traceback, end | Python error, the program saw it |
| start, end | exited cleanly |
| start, then nothing | process was killed - **not** a Python error |

A killed process and a crash look identical in the terminal. Only the missing
end line tells them apart.

On Windows, prefer starting the program via `run.ps1`: the script restores the
terminal even when the program crashes hard and can no longer do so itself.
Otherwise mouse tracking stays on and every mouse move spills control
characters into your prompt.

### If the interface stops responding

A hang leaves no crash report - nothing crashed. Open a **second** terminal
window (macOS: Cmd+N) and collect the evidence there:

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

**Windows (PowerShell, second window):**
```powershell
$p = Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*jira_timesheet*' }
Get-Process -Id $p.ProcessId | Select-Object Id, CPU
Start-Sleep 3
Get-Process -Id $p.ProcessId | Select-Object Id, CPU
```

`CPU` counts processor seconds. Identical in both readings means the program is
waiting; a climbing value means a busy loop. End it with
`Stop-Process -Id $p.ProcessId -Force`.

The CPU column tells the cases apart:

| Reading | What it means |
| --- | --- |
| CPU near 0 %, state `S` | waiting for a network reply - a slow or dropped connection |
| CPU near 100 %, state `R` | busy loop - please report it with the last log lines |
| state `U` (macOS) / `D` (Linux) | stuck in file system access, cannot be killed. Cloud-synced folders (Dropbox, iCloud Drive) are the usual cause - keep the working copy outside of them |

To get out of the hang: `kill <PID>` from the second window, or "Force Quit"
from the Apple menu. Nothing is lost, the settings are written on change.

## License

Apache License 2.0

---

> **Trademark Notice:** "Jira" is a registered trademark of [Atlassian Corporation](https://www.atlassian.com/). This project is not affiliated with, endorsed by, or sponsored by Atlassian.
