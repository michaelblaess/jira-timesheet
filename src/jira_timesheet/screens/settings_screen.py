"""Settings-Dialog auf Basis von BaseSettingsScreen (textual-widgets)."""

from __future__ import annotations

import contextlib
from datetime import date
from pathlib import Path

from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Checkbox, Input, Label, Select, TabPane
from textual_widgets import BaseSettingsScreen

from jira_timesheet.i18n import t
from jira_timesheet.models.settings import Settings
from jira_timesheet.services.cache_service import CACHE_DIR
from jira_timesheet.services.holiday_service import FEDERAL_STATES

# Bundesland-Auswahl, alphabetisch nach Anzeigename sortiert.
_STATE_OPTIONS = [(f"{name} ({code})", code) for code, name in sorted(FEDERAL_STATES.items(), key=lambda x: x[1])]


class SettingsScreen(BaseSettingsScreen):  # type: ignore[misc]
    """App-Settings-Dialog mit Tabs fuer Jira, Export und Berechnung.

    Erbt Look, Sprach-Tab und Save/Cancel-Leiste von BaseSettingsScreen.
    Arbeitet mit einem Settings-Dict; die App konvertiert von/zu der
    Settings-Dataclass.
    """

    DEFAULT_CSS = """
    SettingsScreen .settings-row Input,
    SettingsScreen .settings-row Select {
        width: 1fr;
    }

    SettingsScreen Checkbox {
        margin-bottom: 1;
    }
    """

    def app_tabs(self) -> ComposeResult:
        """Erstellt die app-spezifischen Tabs."""
        with TabPane(t("settings.tab_jira"), id="settings-tab-jira"), VerticalScroll():
            yield from self._text_row("settings.host", "set-host", "jira_host", "https://jira.example.com")
            yield from self._text_row("settings.token", "set-token", "jira_token", "Token", password=True)
            yield from self._text_row("settings.email", "set-email", "email", "user@example.com")
            yield from self._text_row("settings.budget_field", "set-budget-field", "budget_field", "customfield_36461")

        with TabPane(t("settings.tab_export"), id="settings-tab-export"), VerticalScroll():
            yield from self._text_row("settings.logo", "set-logo", "logo_path", "")
            yield Checkbox(
                t("settings.target_export"),
                value=bool(self._settings.get("show_target_hours_in_export", False)),
                id="set-target-export",
            )
            yield Checkbox(
                t("settings.ticket_links_export"),
                value=bool(self._settings.get("show_ticket_links_in_export", False)),
                id="set-ticket-links-export",
            )

        with TabPane(t("settings.tab_calc"), id="settings-tab-calc"), VerticalScroll():
            with Horizontal(classes="settings-row"):
                yield Label(t("settings.federal_state"))
                yield Select(
                    options=_STATE_OPTIONS,
                    value=str(self._settings.get("federal_state", "SN")),
                    allow_blank=False,
                    id="set-federal-state",
                )
            yield from self._text_row("settings.hours_per_day", "set-hours-per-day", "hours_per_day", "8.0")
            yield from self._text_row("settings.max_yearly", "set-max-yearly", "max_yearly_hours", "1720.0")
            yield from self._text_row("settings.hourly_rate", "set-hourly-rate", "hourly_rate", "0")
            year_value = self._settings.get("year", 0)
            year_str = str(year_value) if isinstance(year_value, int) and year_value > 0 else ""
            with Horizontal(classes="settings-row"):
                yield Label(t("settings.year"))
                yield Input(value=year_str, placeholder=str(date.today().year), id="set-year")
            yield from self._text_row("settings.vacation_days", "set-vacation-days", "vacation_days", "30")

    def _text_row(
        self,
        label_key: str,
        widget_id: str,
        settings_key: str,
        placeholder: str,
        password: bool = False,
    ) -> ComposeResult:
        """Baut eine Label/Input-Zeile fuer ein Settings-Feld."""
        raw = self._settings.get(settings_key, "")
        value = "" if raw is None else str(raw)
        with Horizontal(classes="settings-row"):
            yield Label(t(label_key))
            yield Input(value=value, placeholder=placeholder, password=password, id=widget_id)

    def storage_paths(self) -> list[tuple[str, Path]]:
        """Speicherort-Tab: settings.json + Worklog-Cache."""
        return [
            (t("settings.storage.config"), Settings.SETTINGS_FILE),
            (t("settings.storage.cache"), CACHE_DIR),
        ]

    def collect_app_settings(self, settings: dict[str, object]) -> None:
        """Liest die Widget-Werte ins Ergebnis-Dict."""
        settings["jira_host"] = self.query_one("#set-host", Input).value.strip()
        settings["jira_token"] = self.query_one("#set-token", Input).value.strip()
        settings["email"] = self.query_one("#set-email", Input).value.strip()
        settings["budget_field"] = self.query_one("#set-budget-field", Input).value.strip()
        settings["logo_path"] = self.query_one("#set-logo", Input).value.strip()

        settings["show_target_hours_in_export"] = self.query_one("#set-target-export", Checkbox).value
        settings["show_ticket_links_in_export"] = self.query_one("#set-ticket-links-export", Checkbox).value

        state_value = self.query_one("#set-federal-state", Select).value
        if isinstance(state_value, str):
            settings["federal_state"] = state_value

        with contextlib.suppress(ValueError):
            settings["hours_per_day"] = float(self.query_one("#set-hours-per-day", Input).value.strip())
        with contextlib.suppress(ValueError):
            settings["max_yearly_hours"] = float(self.query_one("#set-max-yearly", Input).value.strip())

        rate_str = self.query_one("#set-hourly-rate", Input).value.strip()
        settings["hourly_rate"] = float(rate_str) if self._is_float(rate_str) else 0.0

        year_str = self.query_one("#set-year", Input).value.strip()
        settings["year"] = int(year_str) if year_str.isdigit() else 0

        with contextlib.suppress(ValueError):
            settings["vacation_days"] = int(self.query_one("#set-vacation-days", Input).value.strip())

    @staticmethod
    def _is_float(value: str) -> bool:
        """Prueft, ob ein String als float parsbar ist."""
        if not value:
            return False
        try:
            float(value)
        except ValueError:
            return False
        return True
