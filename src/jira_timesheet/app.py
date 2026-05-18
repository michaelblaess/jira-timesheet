"""Textual App — Hauptanwendung fuer Jira Timesheet."""

from __future__ import annotations

import contextlib
import time
from datetime import date, timedelta

from textual import work
from textual.app import App, ComposeResult
from textual.widgets import DataTable, Footer, Header, TabbedContent, TabPane
from textual_widgets import AboutScreen, HorizontalSplitter, LogPanel, LogRouter

from jira_timesheet import __author__, __version__, __year__
from jira_timesheet.i18n import current_language, t
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

# Projekt-Repository (im About-Dialog verlinkt).
_REPO_URL = "https://github.com/michaelblaess/jira-timesheet"


class JiraTimesheetApp(LogRouter, App):  # type: ignore[misc]
    """TUI fuer Jira Stundenzettel."""

    CSS_PATH = "app.tcss"
    TITLE = f"Jira Timesheet v{__version__} ({__year__})"

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)

        if register_themes is not None:
            register_themes(self)

        self._settings = Settings.load()
        self.theme = self._settings.theme

        self._timesheet: Timesheet | None = None
        self._missing_days: list[tuple] = []
        self._generating = False
        self._anonymized = False

        # Runtime-Bindings mit uebersetzten Labels - class-level BINDINGS
        # koennen kein t() nutzen. Buchstaben-Bindings case-insensitive.
        self._bindings.bind("q,Q", "quit", t("binding.quit"), key_display="q")
        self._bindings.bind("g,G", "generate", t("binding.generate"), key_display="g")
        self._bindings.bind("e,E", "export_excel", t("binding.excel"), key_display="e")
        self._bindings.bind("p,P", "export_pdf", t("binding.pdf"), key_display="p")
        self._bindings.bind("d,D", "show_details", t("binding.details"), key_display="d")
        self._bindings.bind("c,C", "copy_log", t("binding.copy_log"), key_display="c")
        self._bindings.bind("s,S", "show_settings", t("binding.settings"), key_display="s")
        self._bindings.bind("i,I", "show_about", t("binding.info"), key_display="i")
        self._bindings.bind("tab", "next_tab", t("binding.switch_view"), key_display="TAB", priority=True)
        self._bindings.bind("j,J", "show_year", t("binding.year"), key_display="j")
        self._bindings.bind("a,A", "toggle_anon", t("binding.anonymize"), key_display="a")
        self._bindings.bind("r,R", "reset_cache", t("binding.reset_cache"), key_display="r")
        self._bindings.bind("l,L", "toggle_log", t("binding.toggle_log"), key_display="l")
        self._bindings.bind("comma", "prev_month", t("binding.month"), key_display="<")
        self._bindings.bind("full_stop", "next_month", t("binding.month"), key_display=">")

    def compose(self) -> ComposeResult:
        """Erstellt das UI-Layout."""
        yield Header()
        yield ConfigPanel(self._settings, id="config-panel")
        with TabbedContent(id="view-tabs"):
            with TabPane(t("tab.list"), id="tab-list"):
                yield TimesheetTable(
                    hours_per_day=self._settings.hours_per_day,
                    jira_host=self._settings.jira_host,
                    id="timesheet-table",
                )
            with TabPane(t("tab.calendar"), id="tab-calendar"):
                yield CalendarView(
                    hours_per_day=self._settings.hours_per_day,
                    jira_host=self._settings.jira_host,
                    id="calendar-view",
                )
        yield SummaryPanel(id="summary-panel")
        yield HorizontalSplitter(target_id="view-tabs", min_size=10, id="log-splitter")
        yield LogPanel(lang=current_language(), export_name="jira-timesheet", id="log-panel")
        yield Footer()

    def on_mount(self) -> None:
        """Initialisierung nach dem Starten."""
        if not self._settings.log_visible:
            self.query_one("#log-panel", LogPanel).add_class("-log-hidden")
            self.query_one("#log-splitter", HorizontalSplitter).add_class("-log-hidden")

        self._write_log(t("log.ready"))

        if not self._settings.jira_host or not self._settings.jira_token:
            self._write_log(t("log.hint_settings"))

    def watch_theme(self, theme_name: str) -> None:
        """Speichert das Theme bei Aenderung persistent."""
        if not hasattr(self, "_settings"):
            return
        if self._settings.theme == theme_name:
            return
        self._settings.theme = theme_name
        self._settings.save()

    @work(exclusive=True)
    async def action_generate(self) -> None:
        """Generiert den Stundenzettel aus Jira."""
        if self._generating:
            return

        if not self._settings.jira_host:
            self.notify(t("notify.host_not_set"), severity="error")
            return

        if not self._settings.jira_token:
            self.notify(t("notify.token_not_set"), severity="error")
            return

        if not self._settings.email:
            self.notify(t("notify.email_not_set"), severity="error")
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
        self._write_log(
            t(
                "log.start_fetch",
                date_from=f"{config.date_from:%d.%m.%Y}",
                date_to=f"{config.date_to:%d.%m.%Y}",
            )
        )

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
                self._write_log(t("log.from_cache"))
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
                config.date_from,
                config.date_to,
                worked_dates,
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
                self._write_log(t("log.holidays", state=self._settings.federal_state, names=names))

            # Em-Dash-Marker: Luecke vs. Feiertag - sprachneutral.
            gap_count = sum(1 for _, reason in missing_days if "—" in reason)
            if gap_count > 0:
                self._write_log(t("log.gaps", count=gap_count))

            elapsed = time.monotonic() - start_time
            self._write_log(
                t(
                    "log.done",
                    seconds=f"{elapsed:.1f}",
                    days=self._timesheet.working_days,
                    hours=f"{self._timesheet.total_hours:.2f}",
                    target=f"{target_hours:.0f}",
                )
            )

            self._settings.last_date_from = config.date_from.isoformat()
            self._settings.last_date_to = config.date_to.isoformat()
            self._settings.save()

        except JiraClientError as exc:
            self._write_log(t("log.error", error=exc))
            self.notify(str(exc), severity="error")
        except Exception as exc:
            self._write_log(t("log.unexpected_error", error=exc))
            self.notify(t("notify.error", error=exc), severity="error")
        finally:
            self._generating = False
            self.refresh_bindings()

    async def action_export_excel(self) -> None:
        """Exportiert den Stundenzettel als Excel-Datei."""
        if self._timesheet is None:
            self.notify(t("notify.generate_first"), severity="warning")
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
            self._write_log(t("log.excel_saved", url=file_url, path=path))
            self.notify(t("notify.excel_saved", path=path))
        except Exception as exc:
            self._write_log(t("log.excel_error", error=exc))
            self.notify(t("notify.export_error", error=exc), severity="error")

    async def action_export_pdf(self) -> None:
        """Exportiert den Stundenzettel als PDF-Datei."""
        if self._timesheet is None:
            self.notify(t("notify.generate_first"), severity="warning")
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
            self._write_log(t("log.pdf_saved", url=file_url, path=path))
            self.notify(t("notify.pdf_saved", path=path))
        except Exception as exc:
            self._write_log(t("log.pdf_error", error=exc))
            self.notify(t("notify.export_error", error=exc), severity="error")

    def action_show_settings(self) -> None:
        """Oeffnet den Settings-Dialog."""
        from jira_timesheet.screens.settings_screen import SettingsScreen

        self.push_screen(
            SettingsScreen(self._settings.to_dict(), lang=current_language()),
            callback=self._on_settings_closed,
        )

    def _on_settings_closed(self, new_settings: dict[str, object] | None) -> None:
        """Callback nach Schliessen des Settings-Dialogs."""
        if new_settings is None:
            return

        for key, value in new_settings.items():
            if hasattr(self._settings, key):
                setattr(self._settings, key, value)
        self._settings.save()

        config = self.query_one("#config-panel", ConfigPanel)
        config.refresh_display()

    def action_copy_log(self) -> None:
        """Kopiert den Log-Inhalt in die Zwischenablage."""
        self.query_one("#log-panel", LogPanel).copy_log()

    def action_show_about(self) -> None:
        """Zeigt den About-Dialog an."""
        self.push_screen(
            AboutScreen(
                app_name="Jira Timesheet",
                version=__version__,
                author=__author__,
                release=__year__,
                description=t("about.description"),
                lang=current_language(),
                license="Apache 2.0",
                url=_REPO_URL,
            )
        )

    def on_timesheet_table_entry_selected(self, event: TimesheetTable.EntrySelected) -> None:
        """Enter auf einer Zeile — zeigt Details."""
        self._show_entry_details(event.entry)

    def action_show_details(self) -> None:
        """Zeigt Details der aktuell markierten Zeile."""
        try:
            table_widget = self.query_one("#timesheet-table", TimesheetTable)
            dt = table_widget.query_one("#timesheet-data", DataTable)
            row_idx = dt.cursor_row
            if row_idx is not None and row_idx >= 0:
                row = dt.ordered_rows[row_idx]
                entry = table_widget._row_entries.get(row.key.value)
                self._show_entry_details(entry)
        except Exception as exc:
            self._write_log(t("log.details_error", error=exc))

    def _show_entry_details(self, entry: object) -> None:
        """Zeigt Details eines Worklog-Eintrags als Modal."""
        if entry is None:
            return

        from jira_timesheet.screens.detail_screen import DetailScreen

        self.push_screen(DetailScreen(entry, jira_host=self._settings.jira_host))

    @work(exclusive=True)
    async def action_show_year(self) -> None:
        """Laedt Jahresdaten und zeigt die Jahresansicht."""
        if not self._settings.jira_host or not self._settings.jira_token or not self._settings.email:
            self.notify(t("notify.settings_first"), severity="error")
            return

        year = self._settings.year if self._settings.year > 0 else date.today().year
        self._write_log("")
        self._write_log(t("log.year_loading", year=year))

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
                last = date(year, 12, 31) if month == 12 else date(year, month + 1, 1) - timedelta(days=1)

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
                    source = t("source.cache")
                else:
                    self.sub_title = t("subtitle.loading_month", month=t(f"month.{month}"))
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

                self._write_log(
                    t(
                        "log.year_month",
                        month=t(f"month.{month}"),
                        hours=f"{actual:.1f}",
                        days=worked_dates,
                        source=source,
                    )
                )

            self.sub_title = ""

            total = sum(d.get("actual", 0.0) for d in month_data.values())
            self._write_log(
                t(
                    "log.year_done",
                    hours=f"{total:.1f}",
                    fetched=fetched_count,
                    cached=cached_count,
                )
            )

            from jira_timesheet.screens.year_screen import YearScreen

            self.push_screen(
                YearScreen(
                    year=year,
                    month_data=month_data,
                    max_yearly_hours=self._settings.max_yearly_hours,
                    hourly_rate=self._settings.hourly_rate,
                    vacation_days=self._settings.vacation_days,
                    hours_per_day=self._settings.hours_per_day,
                    federal_state=self._settings.federal_state,
                )
            )

        except Exception as exc:
            self.sub_title = ""
            self._write_log(t("log.error", error=exc))
            self.notify(t("notify.error", error=exc), severity="error")

    def action_toggle_anon(self) -> None:
        """Anonymisiert/de-anonymisiert die Daten fuer Screenshots."""
        if self._timesheet is None:
            self.notify(t("notify.generate_first"), severity="warning")
            return

        self._anonymized = not self._anonymized

        table = self.query_one("#timesheet-table", TimesheetTable)
        cal = self.query_one("#calendar-view", CalendarView)

        if self._anonymized:
            from jira_timesheet.services.anonymizer import anonymize_timesheet

            anon_ts = anonymize_timesheet(self._timesheet)
            table.load_timesheet(anon_ts, missing_days=self._missing_days)
            cal.load_timesheet(anon_ts, missing_days=self._missing_days)
            self.sub_title = t("subtitle.anonymized")
            self.notify(t("notify.anonymized"))
        else:
            table.load_timesheet(self._timesheet, missing_days=self._missing_days)
            cal.load_timesheet(self._timesheet, missing_days=self._missing_days)
            self.sub_title = ""
            self.notify(t("notify.deanonymized"))

    def action_reset_cache(self) -> None:
        """Loescht den Worklog-Cache."""
        import shutil

        from jira_timesheet.services.cache_service import CACHE_DIR

        if CACHE_DIR.is_dir():
            count = len(list(CACHE_DIR.glob("*.json")))
            shutil.rmtree(CACHE_DIR)
            self._write_log(t("log.cache_cleared", count=count))
            self.notify(t("notify.cache_cleared", count=count))
        else:
            self._write_log(t("log.cache_empty"))
            self.notify(t("notify.cache_empty"))

    def action_next_tab(self) -> None:
        """Wechselt zum naechsten Tab."""
        tabs = self.query_one("#view-tabs", TabbedContent)
        tabs.active = "tab-calendar" if tabs.active == "tab-list" else "tab-list"

    def action_toggle_log(self) -> None:
        """Blendet den Log-Bereich ein/aus."""
        panel = self.query_one("#log-panel", LogPanel)
        panel.toggle()
        self._apply_log_visibility(not panel.has_class("-log-hidden"))

    def on_log_panel_hidden(self, message: LogPanel.Hidden) -> None:
        """Persistiert das Ausblenden des Logs ueber das Kontextmenue."""
        self._apply_log_visibility(False)

    def _apply_log_visibility(self, visible: bool) -> None:
        """Synchronisiert Splitter und Settings mit der Log-Sichtbarkeit."""
        splitter = self.query_one("#log-splitter", HorizontalSplitter)
        splitter.set_class(not visible, "-log-hidden")
        if not visible:
            # Eine zuvor gezogene Drag-Hoehe zuruecksetzen, sonst bleibt unter
            # den Tabs eine Luecke wo das Log-Panel war.
            self.query_one("#view-tabs").styles.height = "4fr"
        self._settings.log_visible = visible
        self._settings.save()

    def action_prev_month(self) -> None:
        """Wechselt zum vorherigen Monat und laedt Daten."""
        config = self.query_one("#config-panel", ConfigPanel)
        config.prev_month()
        self.action_generate()

    def action_next_month(self) -> None:
        """Wechselt zum naechsten Monat und laedt Daten."""
        config = self.query_one("#config-panel", ConfigPanel)
        config.next_month()
        self.action_generate()

    def check_action(self, action: str, parameters: tuple) -> bool | None:  # type: ignore[override]
        """Steuert die Sichtbarkeit kontextabhaengiger Bindings."""
        # ModalScreen-Isolation: bei offenem Dialog alle App-Bindings sperren.
        if len(self.screen_stack) > 1:
            return None
        if action in ("export_excel", "export_pdf") and self._timesheet is None:
            return None
        return True

    def _write_log(self, message: str) -> None:
        """Schreibt eine Zeile ins Log-Panel."""
        with contextlib.suppress(Exception):
            self.query_one("#log-panel", LogPanel).write_log(message)
