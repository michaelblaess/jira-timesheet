"""Textual App — Hauptanwendung fuer Jira Timesheet."""

from __future__ import annotations

import contextlib
import dataclasses
import re
import time
from collections.abc import Callable
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from textual import work
from textual.app import App, ComposeResult
from textual.widget import Widget
from textual.widgets import DataTable, Footer, Header, TabbedContent, TabPane
from textual_widgets import (
    AboutScreen,
    ClickableLinksMixin,
    CrashGuard,
    HorizontalSplitter,
    LogPanel,
    LogRouter,
)

from jira_timesheet import __author__, __version__, __year__
from jira_timesheet.i18n import current_language, format_number, t
from jira_timesheet.models.settings import Settings
from jira_timesheet.models.timesheet import Timesheet, WorklogEntry
from jira_timesheet.services.anonymizer import FAKE_EMAIL, FAKE_HOST
from jira_timesheet.services.cache_service import CacheService
from jira_timesheet.services.holiday_service import HolidayService
from jira_timesheet.services.jira_client import JiraClient, JiraClientError
from jira_timesheet.services.timesheet_service import TimesheetService
from jira_timesheet.widgets.calendar_view import CalendarView
from jira_timesheet.widgets.config_panel import ConfigPanel
from jira_timesheet.widgets.summary_panel import SummaryPanel
from jira_timesheet.widgets.timesheet_table import TimesheetTable

try:
    from textual_themes import THEME_DISPLAY_NAMES
    from textual_themes import register_all as register_themes
except ImportError:
    register_themes = None  # type: ignore[assignment]
    THEME_DISPLAY_NAMES: dict[str, str] = {}  # type: ignore[no-redef]

# Projekt-Repository (im About-Dialog verlinkt).
_REPO_URL = "https://github.com/michaelblaess/jira-timesheet"


class JiraTimesheetApp(CrashGuard, ClickableLinksMixin, LogRouter, App[None]):  # type: ignore[misc]
    """TUI fuer Jira Stundenzettel."""

    CSS_PATH = "app.tcss"
    TITLE = f"Jira Timesheet v{__version__} ({__year__})"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)

        if register_themes is not None:
            register_themes(self)

        self._settings = Settings.load()
        self.theme = self._settings.theme

        # CrashGuard: lokalisierter Fehler-Dialog statt Total-Absturz.
        self.crash_guard_lang = current_language()

        self._timesheet: Timesheet | None = None
        self._missing_days: list[tuple[date, str]] = []
        self._generating = False
        self._anonymized = False
        # Roh-Log-Zeilen (unzensiert) - ermoeglichen das Neu-Rendern des Logs
        # beim Umschalten der Anonymisierung.
        self._log_lines: list[str] = []
        # Toggle-Zustand fuer den blinkenden Footer-Hinweis (siehe on_mount).
        self._attention_on = False
        # Zuletzt im Speichern-Dialog gewaehltes Verzeichnis (Default: Desktop).
        self._last_export_dir = str(Path.home() / "Desktop")

        # Runtime-Bindings mit uebersetzten Labels - class-level BINDINGS
        # koennen kein t() nutzen. Buchstaben-Bindings case-insensitive.
        self._bindings.bind("q,Q", "quit", t("binding.quit"), key_display="q")
        self._bindings.bind("g,G", "generate", t("binding.generate"), key_display="g")
        self._bindings.bind("e,E", "export_excel", t("binding.excel"), key_display="e")
        self._bindings.bind("p,P", "export_pdf", t("binding.pdf"), key_display="p")
        self._bindings.bind("d,D", "show_details", t("binding.details"), key_display="d")
        # copy_log: Shortcut bleibt, aber nicht im Footer (Log-Kontextmenue
        # bietet "Log kopieren" ohnehin an).
        self._bindings.bind("c,C", "copy_log", t("binding.copy_log"), key_display="c", show=False)
        self._bindings.bind("s,S", "show_settings", t("binding.settings"), key_display="s")
        self._bindings.bind("i,I", "show_about", t("binding.info"), key_display="i")
        self._bindings.bind("tab", "next_tab", t("binding.switch_view"), key_display="TAB", priority=True)
        self._bindings.bind("j,J", "show_year", t("binding.year"), key_display="j")
        self._bindings.bind("a,A", "toggle_anon", t("binding.anonymize"), key_display="a")
        self._bindings.bind("r,R", "reset_cache", t("binding.reset_cache"), key_display="r")
        self._bindings.bind("l,L", "toggle_log", t("binding.toggle_log"), key_display="l")
        self._bindings.bind("t,T", "cycle_theme", t("binding.theme"), key_display="t")
        # Monat-Navigation ist als Klick-Pfeile im ConfigPanel sichtbar -
        # Tastatur-Shortcut bleibt funktional, im Footer aber ausgeblendet.
        self._bindings.bind("comma", "prev_month", t("binding.month"), key_display="<", show=False)
        self._bindings.bind("full_stop", "next_month", t("binding.month"), key_display=">", show=False)

        # Footer-Tooltips - BindingsMap.bind() nimmt kein tooltip-Argument,
        # also nachtraeglich per dataclasses.replace setzen.
        self._apply_binding_tooltips()

    def _apply_binding_tooltips(self) -> None:
        """Ergaenzt jedes Footer-Binding um einen lokalisierten Tooltip.

        ``BindingsMap.bind()`` akzeptiert kein ``tooltip``-Argument, also wird
        nachtraeglich ueber ``key_to_bindings`` iteriert und die Felder via
        ``dataclasses.replace`` ersetzt (``Binding`` ist frozen).
        """
        binding_tooltips = {
            "quit": t("tooltip.quit"),
            "generate": t("tooltip.generate"),
            "export_excel": t("tooltip.excel"),
            "export_pdf": t("tooltip.pdf"),
            "show_details": t("tooltip.details"),
            "show_settings": t("tooltip.settings"),
            "show_about": t("tooltip.info"),
            "next_tab": t("tooltip.switch_view"),
            "show_year": t("tooltip.year"),
            "toggle_anon": t("tooltip.anonymize"),
            "reset_cache": t("tooltip.reset_cache"),
            "toggle_log": t("tooltip.toggle_log"),
            "cycle_theme": t("tooltip.theme"),
        }
        for key, bindings_list in self._bindings.key_to_bindings.items():
            for i, binding in enumerate(bindings_list):
                tooltip = binding_tooltips.get(binding.action)
                if tooltip:
                    self._bindings.key_to_bindings[key][i] = dataclasses.replace(binding, tooltip=tooltip)

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

        # Blinkender Footer-Hinweis lenkt den Blick auf die naechste sinnvolle
        # Aktion: fehlen Settings -> "s" blinkt; sind sie gepflegt, aber noch
        # keine Daten geladen -> "g" blinkt. Manuelles Toggle per Timer statt
        # ANSI-blink, damit es auch auf Windows Terminal funktioniert.
        self.set_interval(0.6, self._tick_attention)

    def _settings_complete(self) -> bool:
        """True, wenn alle fuer das Generieren noetigen Settings gesetzt sind."""
        return bool(self._settings.jira_host) and bool(self._settings.jira_token) and bool(self._settings.email)

    def _tick_attention(self) -> None:
        """Schaltet die Highlight-Klasse auf der jeweils naechsten Aktion an/aus."""
        if not self._settings_complete():
            target = "show_settings"
        elif self._timesheet is None and not self._generating:
            target = "generate"
        else:
            target = ""

        # Nur bei vorhandenem Ziel blinken, sonst Highlight fest aus.
        self._attention_on = not self._attention_on if target else False
        for action in ("show_settings", "generate"):
            key = self._footer_key(action)
            if key is not None:
                key.set_class(action == target and self._attention_on, "-attention")

    def _footer_key(self, action: str) -> Widget | None:
        """Findet die Footer-Taste zu einer Aktion (oder None)."""
        with contextlib.suppress(Exception):
            for footer_key in self.query("FooterKey"):
                if getattr(footer_key, "action", "") == action:
                    return footer_key
        return None

    def watch_theme(self, theme_name: str) -> None:
        """Speichert das Theme bei Aenderung persistent."""
        if not hasattr(self, "_settings"):
            return
        if self._settings.theme == theme_name:
            return
        self._settings.theme = theme_name
        self._settings.save()

    def action_cycle_theme(self) -> None:
        """Wechselt zum naechsten registrierten Theme (alphabetisch sortiert)."""
        names = sorted(self.available_themes.keys())
        if not names:
            return
        try:
            idx = names.index(self.theme)
        except ValueError:
            idx = -1
        next_theme = names[(idx + 1) % len(names)]
        self.theme = next_theme
        # Toast mit Anzeigename (falls vorhanden) - sonst Slug. Persistenz
        # uebernimmt watch_theme.
        display = THEME_DISPLAY_NAMES.get(next_theme, next_theme)
        self.notify(t("notify.theme", name=display))

    def action_generate(self) -> None:
        """g-Taste: explizit neu generieren.

        Erzwingt einen frischen Abruf aus Jira (Cache wird ueberschrieben),
        damit nachtraeglich in Jira eingetragene Worklogs sofort erscheinen -
        auch fuer einen bereits abgeschlossenen Monat.
        """
        self._generate(force_refresh=True)

    @work(exclusive=True)
    async def _generate(self, force_refresh: bool = False) -> None:
        """Generiert den Stundenzettel aus Jira.

        force_refresh=True umgeht den Cache und ruft immer frisch ab. Bei der
        Monats-Navigation (Pfeile) ist es False - dort darf der Cache fuer
        schnelles Blaettern genutzt werden.
        """
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
        # Frisch generierte (echte) Daten -> Anonymisierung zuruecksetzen, bevor
        # die erste Log-Zeile geschrieben wird. Tabelle, Kalender, Summary und
        # Log zeigen dann konsistent echte Werte; 'a' zensiert alles gemeinsam.
        self._anonymized = False
        config = self.query_one("#config-panel", ConfigPanel)
        config.set_anonymized(False)
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

            if not force_refresh and CacheService.has_cache(m_year, m_month, self._settings.email):
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
                    seconds=format_number(elapsed, 1),
                    days=self._timesheet.working_days,
                    hours=format_number(self._timesheet.total_hours, 2),
                    target=format_number(target_hours, 0),
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

    def action_export_excel(self) -> None:
        """Oeffnet den Speichern-Dialog und exportiert als Excel-Datei."""
        from jira_timesheet.services.excel_exporter import ExcelExporter

        if self._timesheet is None:
            self.notify(t("notify.generate_first"), severity="warning")
            return

        suggested = ExcelExporter.suggested_filename(self._timesheet)
        self._open_save_dialog(
            suggested,
            (t("save_dialog.filter_excel"), lambda p: p.suffix.lower() == ".xlsx"),
            self._do_export_excel,
        )

    def action_export_pdf(self) -> None:
        """Oeffnet den Speichern-Dialog und exportiert als PDF-Datei."""
        from jira_timesheet.services.pdf_exporter import PdfExporter

        if self._timesheet is None:
            self.notify(t("notify.generate_first"), severity="warning")
            return

        suggested = PdfExporter.suggested_filename(self._timesheet)
        self._open_save_dialog(
            suggested,
            (t("save_dialog.filter_pdf"), lambda p: p.suffix.lower() == ".pdf"),
            self._do_export_pdf,
        )

    def _open_save_dialog(
        self,
        suggested_name: str,
        file_filter: tuple[str, Callable[[Path], bool]],
        callback: Callable[[Path | None], None],
    ) -> None:
        """Zeigt den File-Save-Dialog (textual-fspicker) und ruft ``callback`` mit dem Pfad."""
        from textual_fspicker import FileSave, Filters

        self.push_screen(
            FileSave(
                location=self._last_export_dir,
                title=t("save_dialog.title"),
                save_button=t("save_dialog.save_button"),
                cancel_button=t("save_dialog.cancel_button"),
                default_file=suggested_name,
                filters=Filters(
                    file_filter,
                    (t("save_dialog.filter_all"), lambda p: True),
                ),
            ),
            callback=callback,
        )

    def _export_context(self) -> tuple[list[tuple[date, str]], float]:
        """Berechnet fehlende Arbeitstage und Soll-Stunden fuer den Export."""
        holiday_svc = HolidayService(self._settings.federal_state)
        config = self.query_one("#config-panel", ConfigPanel)
        assert self._timesheet is not None
        worked_dates = {e.date for e in self._timesheet.all_entries}
        missing = holiday_svc.get_missing_workdays(config.date_from, config.date_to, worked_dates)
        target_wd = holiday_svc.count_workdays(config.date_from, config.date_to)
        target_h = target_wd * self._settings.hours_per_day
        export_target_h = target_h if self._settings.show_target_hours_in_export else 0.0
        return missing, export_target_h

    def _do_export_excel(self, target: Path | None) -> None:
        """Callback des Speichern-Dialogs: schreibt die Excel-Datei."""
        if target is None or self._timesheet is None:
            return
        try:
            from jira_timesheet.services.excel_exporter import ExcelExporter

            missing, export_target_h = self._export_context()
            exporter = ExcelExporter(
                logo_path=self._settings.logo_path,
                jira_host=self._settings.jira_host,
                hours_per_day=self._settings.hours_per_day,
                show_ticket_links=self._settings.show_ticket_links_in_export,
            )
            path = exporter.export(
                self._timesheet,
                missing_days=missing,
                target_hours=export_target_h,
                output_path=str(target),
            )
            self._last_export_dir = str(target.parent)
            self._write_log(t("log.excel_saved", link=self.link_markup(path, path)))
            self.notify(t("notify.excel_saved", path=path))
        except Exception as exc:
            self._write_log(t("log.excel_error", error=exc))
            self.notify(t("notify.export_error", error=exc), severity="error")

    def _do_export_pdf(self, target: Path | None) -> None:
        """Callback des Speichern-Dialogs: schreibt die PDF-Datei."""
        if target is None or self._timesheet is None:
            return
        try:
            from jira_timesheet.services.pdf_exporter import PdfExporter

            missing, export_target_h = self._export_context()
            exporter = PdfExporter(
                logo_path=self._settings.logo_path,
                jira_host=self._settings.jira_host,
                hours_per_day=self._settings.hours_per_day,
            )
            path = exporter.export(
                self._timesheet,
                missing_days=missing,
                target_hours=export_target_h,
                output_path=str(target),
            )
            self._last_export_dir = str(target.parent)
            self._write_log(t("log.pdf_saved", link=self.link_markup(path, path)))
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
        # Im Kalender gibt es keine markierbare Ticket-Zeile - Aktion ist dort
        # ueber check_action deaktiviert, hier zur Sicherheit nochmal abfangen.
        if self._active_tab() == "tab-calendar":
            return
        # Ohne geladenen Stundenzettel gibt es keine Zeile - gleicher
        # Toast wie bei Excel/PDF-Export.
        if self._timesheet is None:
            self.notify(t("notify.generate_first"), severity="warning")
            return

        try:
            table_widget = self.query_one("#timesheet-table", TimesheetTable)
            dt = table_widget.query_one("#timesheet-data", DataTable)
            row_idx = dt.cursor_row
            if row_idx is None or row_idx < 0 or row_idx >= len(dt.ordered_rows):
                return
            row = dt.ordered_rows[row_idx]
            entry = table_widget._row_entries.get(str(row.key.value))
            self._show_entry_details(entry)
        except Exception as exc:
            self._write_log(t("log.details_error", error=exc))

    def _show_entry_details(self, entry: WorklogEntry | None) -> None:
        """Zeigt Details eines Worklog-Eintrags als Modal."""
        if entry is None:
            return

        from jira_timesheet.screens.detail_screen import DetailScreen

        # Im Anonymisierungs-Modus den Host im Ticket-Link faken, sonst leakt
        # die echte Server-Adresse in der angezeigten URL.
        host = FAKE_HOST if self._anonymized else self._settings.jira_host
        self.push_screen(DetailScreen(entry, jira_host=host))

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
        month_data: dict[int, dict[str, Any]] = {}

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
                        hours=format_number(actual, 1),
                        days=worked_dates,
                        source=source,
                    )
                )

            self.sub_title = ""

            total = sum(d.get("actual", 0.0) for d in month_data.values())
            self._write_log(
                t(
                    "log.year_done",
                    hours=format_number(total, 1),
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
                    anonymized=self._anonymized,
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
        summary = self.query_one("#summary-panel", SummaryPanel)
        config = self.query_one("#config-panel", ConfigPanel)
        # Geldbetraege (Netto/Brutto) im Summary zensieren bzw. wieder zeigen.
        summary.set_anonymized(self._anonymized)
        # Host + E-Mail im Config-Header zensieren bzw. wieder zeigen.
        config.set_anonymized(self._anonymized)
        # Log neu rendern, damit E-Mail/Host in bereits geschriebenen Zeilen
        # zensiert bzw. wieder gezeigt werden.
        self._rerender_log()

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
        """Wechselt zum vorherigen Monat (Generate folgt via MonthChanged)."""
        self.query_one("#config-panel", ConfigPanel).prev_month()

    def action_next_month(self) -> None:
        """Wechselt zum naechsten Monat (Generate folgt via MonthChanged)."""
        self.query_one("#config-panel", ConfigPanel).next_month()

    def on_config_panel_month_changed(self, event: ConfigPanel.MonthChanged) -> None:
        """Reagiert auf die Zeitraum-Pfeile im ConfigPanel (Tastatur + Maus)."""
        # Navigation darf den Cache nutzen (schnelles Blaettern) - nur die
        # g-Taste (action_generate) erzwingt einen frischen Abruf.
        self._generate(force_refresh=False)

    def check_action(self, action: str, parameters: tuple[object, ...]) -> bool | None:
        """Steuert die Sichtbarkeit kontextabhaengiger Bindings."""
        # ModalScreen-Isolation: bei offenem Dialog alle App-Bindings sperren.
        if len(self.screen_stack) > 1:
            return None
        if action in ("export_excel", "export_pdf") and self._timesheet is None:
            return None
        # "Details" gibt es nur in der Listenansicht - im Kalender kann keine
        # Ticket-Zeile markiert werden, daher dort deaktivieren (dimmen).
        return not (action == "show_details" and self._active_tab() == "tab-calendar")

    def _active_tab(self) -> str:
        """Liefert die id des aktiven View-Tabs (oder '' wenn nicht ermittelbar)."""
        with contextlib.suppress(Exception):
            return self.query_one("#view-tabs", TabbedContent).active
        return ""

    def on_tabbed_content_tab_activated(self, event: TabbedContent.TabActivated) -> None:
        """Footer neu bewerten - 'Details' ist nur in der Listenansicht aktiv."""
        self.refresh_bindings()

    def _write_log(self, message: str) -> None:
        """Schreibt eine Zeile ins Log-Panel; http(s)-URLs werden klickbar.

        Die Rohzeile wird gepuffert, damit das Log beim Umschalten der
        Anonymisierung neu (zensiert) gerendert werden kann.
        """
        self._log_lines.append(message)
        with contextlib.suppress(Exception):
            self.query_one("#log-panel", LogPanel).write_log(self._render_log_line(message))

    def _render_log_line(self, message: str) -> str:
        """Bereitet eine Log-Zeile auf.

        Im Anonymisierungs-Modus werden E-Mail- und Host-Adressen zensiert,
        anschliessend werden http(s)-URLs klickbar gemacht.
        """
        text = self._mask_sensitive(message) if self._anonymized else message
        # str(): linkify_urls ist untypisiert (Any) -> no-any-return vermeiden.
        return str(self.linkify_urls(text))

    def _mask_sensitive(self, message: str) -> str:
        """Ersetzt die Jira-Host-Adresse und E-Mail-Adressen durch Fakes."""
        masked = message
        host = self._settings.jira_host
        if host:
            masked = masked.replace(host, FAKE_HOST)
            # Host auch ohne Schema (z.B. nackte Domain) ersetzen.
            host_domain = host.split("://", 1)[-1].rstrip("/")
            fake_domain = FAKE_HOST.split("://", 1)[-1]
            if host_domain:
                masked = masked.replace(host_domain, fake_domain)
        # Alle E-Mail-aehnlichen Tokens auf einen Fake mappen (deckt die
        # konfigurierte Adresse UND evtl. weitere ab, z.B. in der JQL).
        masked = re.sub(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}", FAKE_EMAIL, masked)
        return masked

    def _rerender_log(self) -> None:
        """Rendert das komplette Log aus dem Puffer neu.

        Wird beim Umschalten der Anonymisierung aufgerufen, damit auch bereits
        geschriebene Zeilen (E-Mail/Host) zensiert bzw. wieder gezeigt werden.
        """
        with contextlib.suppress(Exception):
            panel = self.query_one("#log-panel", LogPanel)
            panel.clear_log()
            for line in self._log_lines:
                panel.write_log(self._render_log_line(line))
