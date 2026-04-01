"""Textual App — Hauptanwendung fuer Jira Timesheet."""
from __future__ import annotations

import time
from datetime import datetime

from textual import work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Footer, Header, RichLog

from jira_timesheet import __version__, __year__
from jira_timesheet.models.settings import Settings
from jira_timesheet.models.timesheet import Timesheet
from jira_timesheet.services.holiday_service import HolidayService
from jira_timesheet.services.jira_client import JiraClient, JiraClientError
from jira_timesheet.services.timesheet_service import TimesheetService
from jira_timesheet.widgets.config_panel import ConfigPanel
from jira_timesheet.widgets.summary_panel import SummaryPanel
from jira_timesheet.widgets.timesheet_table import TimesheetTable

try:
    from textual_themes import register_all as register_themes
except ImportError:
    register_themes = None  # type: ignore[assignment]


class JiraTimesheetApp(App):
    """TUI fuer Jira Stundenzettel."""

    CSS_PATH = "app.tcss"
    TITLE = f"Jira Timesheet v{__version__} ({__year__})"

    BINDINGS = [
        Binding("q", "quit", "Beenden"),
        Binding("g", "generate", "Generieren"),
        Binding("e", "export_excel", "Excel"),
        Binding("p", "export_pdf", "PDF"),
        Binding("c", "copy_log", "Log kopieren"),
        Binding("s", "show_settings", "Settings"),
        Binding("i", "show_info", "Info"),
        Binding("l", "toggle_log", "Log"),
        Binding("left", "prev_month", "◄ Monat", show=False),
        Binding("right", "next_month", "► Monat", show=False),
    ]

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)

        if register_themes is not None:
            register_themes(self)

        self._settings = Settings.load()
        self.theme = self._settings.theme

        self._timesheet: Timesheet | None = None
        self._generating = False

    def compose(self) -> ComposeResult:
        """Erstellt das UI-Layout."""
        yield Header()
        yield ConfigPanel(self._settings, id="config-panel")
        yield TimesheetTable(
            hours_per_day=self._settings.hours_per_day,
            jira_host=self._settings.jira_host,
            id="timesheet-table",
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

        table.clear_table()
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

            entries = await client.get_worklogs(
                email=self._settings.email,
                date_from=config.date_from,
                date_to=config.date_to,
            )

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

            table.load_timesheet(self._timesheet, missing_days=missing_days)
            summary.update_timesheet(self._timesheet, target_hours=target_hours)

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
            )
            path = exporter.export(self._timesheet, missing_days=missing, target_hours=target_h)
            self._write_log(f"[green]Excel gespeichert: {path}[/green]")
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
            path = exporter.export(self._timesheet, missing_days=missing, target_hours=target_h)
            self._write_log(f"[green]PDF gespeichert: {path}[/green]")
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
