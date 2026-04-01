"""Textual App — Hauptanwendung fuer Jira Timesheet."""
from __future__ import annotations

import time
from datetime import date, datetime, timedelta

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, RichLog

from jira_timesheet import __version__, __year__
from jira_timesheet.models.settings import Settings
from jira_timesheet.models.timesheet import Timesheet
from jira_timesheet.services.cache_service import CacheService
from jira_timesheet.services.holiday_service import HolidayService
from jira_timesheet.services.jira_client import JiraClient, JiraClientError
from jira_timesheet.services.timesheet_service import TimesheetService
from jira_timesheet.widgets.calendar_view import CalendarView
from jira_timesheet.widgets.config_panel import ConfigPanel
from jira_timesheet.widgets.summary_panel import SummaryPanel
from jira_timesheet.widgets.timesheet_table import TimesheetTable

try:
    from textual_themes import register_all as register_themes
except ImportError:
    register_themes = None  # type: ignore[assignment]

_MONTH_NAMES = [
    "Januar", "Februar", "Maerz", "April", "Mai", "Juni",
    "Juli", "August", "September", "Oktober", "November", "Dezember",
]


class JiraTimesheetApp(App):
    """TUI fuer Jira Stundenzettel."""

    CSS_PATH = "app.tcss"
    TITLE = f"Jira Timesheet v{__version__} ({__year__})"

    BINDINGS = [
        Binding("q", "quit", "Beenden"),
        Binding("g", "generate", "Generieren"),
        Binding("e", "export_excel", "Excel"),
        Binding("p", "export_pdf", "PDF"),
        Binding("d", "show_details", "Details"),
        Binding("c", "copy_log", "Log kopieren"),
        Binding("s", "show_settings", "Settings"),
        Binding("i", "show_info", "Info"),
        Binding("tab", "toggle_view", "View wechseln", key_display="TAB", priority=True),
        Binding("j", "show_year", "Jahr"),
        Binding("l", "toggle_log", "Log"),
        Binding("comma", "prev_month", "Monat", key_display="<"),
        Binding("full_stop", "next_month", "Monat", key_display=">"),
    ]

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)

        if register_themes is not None:
            register_themes(self)

        self._settings = Settings.load()
        self.theme = self._settings.theme

        self._timesheet: Timesheet | None = None
        self._missing_days: list[tuple] = []
        self._generating = False
        self._calendar_active = False

    def compose(self) -> ComposeResult:
        """Erstellt das UI-Layout."""
        yield Header()
        yield ConfigPanel(self._settings, id="config-panel")
        yield TimesheetTable(
            hours_per_day=self._settings.hours_per_day,
            jira_host=self._settings.jira_host,
            id="timesheet-table",
        )
        yield CalendarView(
            hours_per_day=self._settings.hours_per_day,
            jira_host=self._settings.jira_host,
            id="calendar-view",
        )
        yield SummaryPanel(id="summary-panel")
        yield RichLog(id="log-panel", highlight=True, markup=True)
        yield Footer()

    def on_mount(self) -> None:
        """Initialisierung nach dem Starten."""
        if not self._settings.log_visible:
            log = self.query_one("#log-panel", RichLog)
            log.add_class("hidden")

        self._write_log("Bereit. Druecke [bold][G][/bold] um den Stundenzettel zu generieren.")

        if not self._settings.jira_host or not self._settings.jira_token:
            self._write_log(
                "[yellow]Hinweis: Jira Host und/oder Token nicht gesetzt. "
                "Druecke [bold][S][/bold] fuer Settings.[/yellow]"
            )

    def watch_theme(self, theme_name: str) -> None:
        """Speichert das Theme bei Aenderung persistent."""
        self._settings.theme = theme_name
        self._settings.save()

    @work(exclusive=True)
    async def action_generate(self) -> None:
        """Generiert den Stundenzettel aus Jira."""
        if self._generating:
            return

        if not self._settings.jira_host:
            self.notify("Jira Host nicht gesetzt! Druecke [S] fuer Settings.", severity="error")
            return

        if not self._settings.jira_token:
            self.notify("Jira Token nicht gesetzt! Druecke [S] fuer Settings.", severity="error")
            return

        if not self._settings.email:
            self.notify("E-Mail nicht gesetzt! Druecke [S] fuer Settings.", severity="error")
            return

        self._generating = True
        config = self.query_one("#config-panel", ConfigPanel)
        table = self.query_one("#timesheet-table", TimesheetTable)
        summary = self.query_one("#summary-panel", SummaryPanel)

        cal = self.query_one("#calendar-view", CalendarView)

        table.clear_table()
        cal.clear_calendar()
        summary.clear()

        start_time = time.monotonic()
        self._write_log("")
        self._write_log(f"[bold]Starte Abruf fuer {config.date_from:%d.%m.%Y} — {config.date_to:%d.%m.%Y}[/bold]")

        try:
            client = JiraClient(
                host=self._settings.jira_host,
                token=self._settings.jira_token,
                budget_field=self._settings.budget_field,
                on_log=self._write_log,
            )

            m_year = config.date_from.year
            m_month = config.date_from.month

            if CacheService.has_cache(m_year, m_month, self._settings.email):
                entries = CacheService.load(m_year, m_month, self._settings.email)
                self._write_log("[dim]Daten aus Cache geladen[/dim]")
            else:
                entries = await client.get_worklogs(
                    email=self._settings.email,
                    date_from=config.date_from,
                    date_to=config.date_to,
                )
                CacheService.save(m_year, m_month, self._settings.email, entries)

            developer = entries[0].author if entries else self._settings.email
            self._timesheet = TimesheetService.build_timesheet(
                entries=entries,
                developer=developer,
                email=self._settings.email,
                date_from=config.date_from,
                date_to=config.date_to,
            )

            holiday_svc = HolidayService(self._settings.federal_state)
            worked_dates = {e.date for e in entries}
            missing_days = holiday_svc.get_missing_workdays(
                config.date_from, config.date_to, worked_dates,
            )
            target_workdays = holiday_svc.count_workdays(config.date_from, config.date_to)
            target_hours = target_workdays * self._settings.hours_per_day

            self._missing_days = missing_days

            table.load_timesheet(self._timesheet, missing_days=missing_days)
            cal.load_timesheet(self._timesheet, missing_days=missing_days)
            summary.update_timesheet(
                self._timesheet,
                target_hours=target_hours,
                hourly_rate=self._settings.hourly_rate,
            )

            holidays_in_range = holiday_svc.get_holidays_in_range(config.date_from, config.date_to)
            if holidays_in_range:
                names = ", ".join(f"{d:%d.%m.} {n}" for d, n in holidays_in_range.items())
                self._write_log(f"Feiertage ({self._settings.federal_state}): {names}")

            gap_count = sum(1 for _, reason in missing_days if "\u2014" in reason)
            if gap_count > 0:
                self._write_log(f"[yellow]{gap_count} Arbeitstag(e) ohne Eintrag[/yellow]")

            elapsed = time.monotonic() - start_time
            self._write_log(
                f"[green]Fertig in {elapsed:.1f}s — "
                f"{self._timesheet.working_days} Tage, "
                f"{self._timesheet.total_hours:.2f}h "
                f"(Soll: {target_hours:.0f}h)[/green]"
            )

            self._settings.last_date_from = config.date_from.isoformat()
            self._settings.last_date_to = config.date_to.isoformat()
            self._settings.save()

        except JiraClientError as exc:
            self._write_log(f"[red bold]Fehler: {exc}[/red bold]")
            self.notify(str(exc), severity="error")
        except Exception as exc:
            self._write_log(f"[red bold]Unerwarteter Fehler: {exc}[/red bold]")
            self.notify(f"Fehler: {exc}", severity="error")
        finally:
            self._generating = False
            self.refresh_bindings()

    async def action_export_excel(self) -> None:
        """Exportiert den Stundenzettel als Excel-Datei."""
        if self._timesheet is None:
            self.notify("Erst Stundenzettel generieren [G]", severity="warning")
            return

        try:
            from jira_timesheet.services.excel_exporter import ExcelExporter

            holiday_svc = HolidayService(self._settings.federal_state)
            config = self.query_one("#config-panel", ConfigPanel)
            worked_dates = {e.date for e in self._timesheet.all_entries}
            missing = holiday_svc.get_missing_workdays(config.date_from, config.date_to, worked_dates)
            target_wd = holiday_svc.count_workdays(config.date_from, config.date_to)
            target_h = target_wd * self._settings.hours_per_day

            exporter = ExcelExporter(
                logo_path=self._settings.logo_path,
                jira_host=self._settings.jira_host,
                hours_per_day=self._settings.hours_per_day,
                show_ticket_links=self._settings.show_ticket_links_in_export,
            )
            export_target_h = target_h if self._settings.show_target_hours_in_export else 0.0
            path = exporter.export(self._timesheet, missing_days=missing, target_hours=export_target_h)
            file_url = "file:///" + path.replace("\\", "/")
            self._write_log(f"[green]Excel gespeichert: [link={file_url}]{path}[/link][/green]")
            self.notify(f"Excel: {path}")
        except Exception as exc:
            self._write_log(f"[red]Excel-Export Fehler: {exc}[/red]")
            self.notify(f"Excel-Export Fehler: {exc}", severity="error")

    async def action_export_pdf(self) -> None:
        """Exportiert den Stundenzettel als PDF-Datei."""
        if self._timesheet is None:
            self.notify("Erst Stundenzettel generieren [G]", severity="warning")
            return

        try:
            from jira_timesheet.services.pdf_exporter import PdfExporter

            holiday_svc = HolidayService(self._settings.federal_state)
            config = self.query_one("#config-panel", ConfigPanel)
            worked_dates = {e.date for e in self._timesheet.all_entries}
            missing = holiday_svc.get_missing_workdays(config.date_from, config.date_to, worked_dates)
            target_wd = holiday_svc.count_workdays(config.date_from, config.date_to)
            target_h = target_wd * self._settings.hours_per_day

            exporter = PdfExporter(
                logo_path=self._settings.logo_path,
                jira_host=self._settings.jira_host,
                hours_per_day=self._settings.hours_per_day,
            )
            export_target_h = target_h if self._settings.show_target_hours_in_export else 0.0
            path = exporter.export(self._timesheet, missing_days=missing, target_hours=export_target_h)
            file_url = "file:///" + path.replace("\\", "/")
            self._write_log(f"[green]PDF gespeichert: [link={file_url}]{path}[/link][/green]")
            self.notify(f"PDF: {path}")
        except Exception as exc:
            self._write_log(f"[red]PDF-Export Fehler: {exc}[/red]")
            self.notify(f"PDF-Export Fehler: {exc}", severity="error")

    def action_show_settings(self) -> None:
        """Oeffnet den Settings-Dialog."""
        from jira_timesheet.screens.settings_screen import SettingsScreen

        self.push_screen(SettingsScreen(self._settings), callback=self._on_settings_closed)

    def _on_settings_closed(self, changed: bool | None) -> None:
        """Callback nach Schliessen des Settings-Dialogs."""
        if changed:
            self._settings.save()
            config = self.query_one("#config-panel", ConfigPanel)
            config.refresh_display()
            self._write_log("[green]Settings gespeichert.[/green]")

    def action_copy_log(self) -> None:
        """Kopiert den Log-Inhalt in die Zwischenablage."""
        try:
            log = self.query_one("#log-panel", RichLog)
            plain_lines: list[str] = []
            for line in log.lines:
                plain_lines.append(line.text if hasattr(line, "text") else "".join(seg.text for seg in line))
            text = "\n".join(plain_lines)
            self.copy_to_clipboard(text)
            self.notify("Log in Zwischenablage kopiert")
        except Exception as exc:
            self.notify(f"Kopieren fehlgeschlagen: {exc}", severity="error")

    def action_show_info(self) -> None:
        """Zeigt den Info-Dialog an."""
        from jira_timesheet.screens.info_screen import InfoScreen

        self.push_screen(InfoScreen())

    def on_timesheet_table_entry_selected(self, event: TimesheetTable.EntrySelected) -> None:
        """Enter auf einer Zeile — zeigt Details."""
        self._show_entry_details(event.entry)

    def action_show_details(self) -> None:
        """Zeigt Details der aktuell markierten Zeile."""
        try:
            table_widget = self.query_one("#timesheet-table", TimesheetTable)
            dt = table_widget.query_one("#timesheet-data", DataTable)
            row_key = dt.cursor_row
            if row_key is not None:
                key = str(list(dt.rows.keys())[row_key])
                entry = table_widget._row_entries.get(key)
                self._show_entry_details(entry)
        except Exception:
            pass

    def _show_entry_details(self, entry: object) -> None:
        """Zeigt Details eines Worklog-Eintrags im Log."""
        if entry is None:
            return

        self._write_log("")
        self._write_log(f"[bold]{entry.ticket}[/bold] — {entry.summary}")
        self._write_log(f"  Worklog: {entry.date:%d.%m.%Y}  |  {entry.hours:.2f}h  |  Autor: {entry.author}")

        if entry.assignee:
            self._write_log(f"  Bearbeiter: {entry.assignee}")

        line1: list[str] = []
        if entry.issuetype:
            line1.append(f"Typ: {entry.issuetype}")
        if entry.status:
            line1.append(f"Status: {entry.status}")
        if entry.resolution:
            line1.append(f"Loesung: {entry.resolution}")
        if entry.priority:
            line1.append(f"Prioritaet: {entry.priority}")
        if line1:
            self._write_log(f"  {' | '.join(line1)}")

        line2: list[str] = []
        if entry.budget:
            line2.append(f"Budget: {entry.budget}")
        if entry.components:
            line2.append(f"Komponenten: {entry.components}")
        if entry.labels:
            line2.append(f"Labels: {entry.labels}")
        if line2:
            self._write_log(f"  {' | '.join(line2)}")

        line3: list[str] = []
        if entry.created:
            line3.append(f"Erstellt: {entry.created}")
        if entry.updated:
            line3.append(f"Aktualisiert: {entry.updated}")
        if entry.total_logged:
            line3.append(f"Gesamt-Protokolliert: {entry.total_logged}")
        if line3:
            self._write_log(f"  {' | '.join(line3)}")

        if self._settings.jira_host and entry.ticket:
            url = f"{self._settings.jira_host}/browse/{entry.ticket}"
            self._write_log(f"  [link={url}]{url}[/link]")

    @work(exclusive=True)
    async def action_show_year(self) -> None:
        """Laedt Jahresdaten und zeigt die Jahresansicht."""
        if not self._settings.jira_host or not self._settings.jira_token or not self._settings.email:
            self.notify("Erst Settings konfigurieren [S]", severity="error")
            return

        year = self._settings.year if self._settings.year > 0 else date.today().year
        self._write_log("")
        self._write_log(f"[bold]Lade Jahresdaten {year}...[/bold]")

        holiday_svc = HolidayService(self._settings.federal_state)
        month_data: dict[int, dict] = {}

        try:
            client = JiraClient(
                host=self._settings.jira_host,
                token=self._settings.jira_token,
                budget_field=self._settings.budget_field,
            )

            cached_count = 0
            fetched_count = 0

            for month in range(1, 13):
                first = date(year, month, 1)
                if month == 12:
                    last = date(year, 12, 31)
                else:
                    last = date(year, month + 1, 1) - timedelta(days=1)

                target_days = holiday_svc.count_workdays(first, last)
                target_h = target_days * self._settings.hours_per_day

                if first > date.today():
                    month_data[month] = {
                        "actual": 0.0,
                        "target": target_h,
                        "working_days": 0,
                        "target_days": target_days,
                    }
                    continue

                # Cache pruefen fuer abgeschlossene Monate
                if CacheService.has_cache(year, month, self._settings.email):
                    entries = CacheService.load(year, month, self._settings.email)
                    cached_count += 1
                    source = "[dim](Cache)[/dim]"
                else:
                    self.sub_title = f"Lade {_MONTH_NAMES[month - 1]}..."
                    entries = await client.get_worklogs(
                        email=self._settings.email,
                        date_from=first,
                        date_to=last,
                    )
                    fetched_count += 1
                    source = ""

                    # Abgeschlossene Monate cachen
                    CacheService.save(year, month, self._settings.email, entries)

                actual = sum(e.hours for e in entries)
                worked_dates = len({e.date for e in entries})

                month_data[month] = {
                    "actual": actual,
                    "target": target_h,
                    "working_days": worked_dates,
                    "target_days": target_days,
                }

                self._write_log(f"  {_MONTH_NAMES[month - 1]}: {actual:.1f}h ({worked_dates} Tage) {source}")

            self.sub_title = ""

            total = sum(d.get("actual", 0.0) for d in month_data.values())
            self._write_log(
                f"[green]Jahresdaten geladen: {total:.1f}h "
                f"({fetched_count} abgerufen, {cached_count} aus Cache)[/green]"
            )

            from jira_timesheet.screens.year_screen import YearScreen
            self.push_screen(YearScreen(
                year=year,
                month_data=month_data,
                max_yearly_hours=self._settings.max_yearly_hours,
                hourly_rate=self._settings.hourly_rate,
                vacation_days=self._settings.vacation_days,
                hours_per_day=self._settings.hours_per_day,
                federal_state=self._settings.federal_state,
            ))

        except Exception as exc:
            self.sub_title = ""
            self._write_log(f"[red bold]Fehler: {exc}[/red bold]")
            self.notify(f"Fehler: {exc}", severity="error")

    def action_toggle_view(self) -> None:
        """Wechselt zwischen Listen- und Kalenderansicht."""
        table = self.query_one("#timesheet-table", TimesheetTable)
        cal = self.query_one("#calendar-view", CalendarView)

        self._calendar_active = not self._calendar_active

        if self._calendar_active:
            table.add_class("hidden")
            cal.add_class("visible")
            self.sub_title = "Kalenderansicht"
        else:
            table.remove_class("hidden")
            cal.remove_class("visible")
            self.sub_title = ""

    def action_toggle_log(self) -> None:
        """Blendet den Log-Bereich ein/aus."""
        log = self.query_one("#log-panel", RichLog)
        log.toggle_class("hidden")
        self._settings.log_visible = not log.has_class("hidden")
        self._settings.save()

    def action_prev_month(self) -> None:
        """Wechselt zum vorherigen Monat."""
        config = self.query_one("#config-panel", ConfigPanel)
        config.prev_month()

    def action_next_month(self) -> None:
        """Wechselt zum naechsten Monat."""
        config = self.query_one("#config-panel", ConfigPanel)
        config.next_month()

    def check_action(self, action: str, parameters: tuple) -> bool | None:  # type: ignore[override]
        """Blendet Export-Aktionen aus wenn kein Timesheet vorhanden."""
        if action in ("export_excel", "export_pdf") and self._timesheet is None:
            return None
        return True

    def _write_log(self, message: str) -> None:
        """Schreibt eine Zeile ins Log mit Timestamp."""
        try:
            log = self.query_one("#log-panel", RichLog)
            timestamp = datetime.now().strftime("%H:%M:%S")
            log.write(f"[dim]{timestamp}[/dim] {message}")
        except Exception:
            pass
