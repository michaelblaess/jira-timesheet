"""Settings-Dialog auf Basis von BaseSettingsScreen (textual-widgets)."""

from __future__ import annotations

import contextlib
from datetime import date
from pathlib import Path

from textual import on, work
from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.widgets import Button, Checkbox, Input, Label, Select, Static, TabPane
from textual_widgets import BaseSettingsScreen

from jira_timesheet.i18n import t
from jira_timesheet.models.settings import Settings
from jira_timesheet.services.cache_service import CACHE_DIR
from jira_timesheet.services.holiday_service import FEDERAL_STATES
from jira_timesheet.services.jira_client import JiraClient, JiraClientError

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

    SettingsScreen .hint {
        color: $text-muted;
        padding: 1 1;
        margin-top: 1;
        border: round $surface-lighten-2;
    }

    SettingsScreen .label-with-icon {
        width: 26;
        height: 1;
    }

    SettingsScreen .label-with-icon Label {
        width: auto;
        padding: 0 1 0 1;
    }

    SettingsScreen .info-icon {
        width: auto;
        height: 1;
        color: cyan;
        text-style: bold;
        padding: 0 1 0 0;
    }

    SettingsScreen .info-icon:hover {
        color: white;
        background: cyan 30%;
    }

    SettingsScreen #budget-row Input {
        width: 1fr;
    }

    SettingsScreen #budget-row Button {
        width: auto;
        margin-left: 1;
        margin-right: 2;
    }
    """

    def app_tabs(self) -> ComposeResult:
        """Erstellt die app-spezifischen Tabs."""
        with TabPane(t("settings.tab_jira"), id="settings-tab-jira"), VerticalScroll():
            yield from self._text_row(
                "settings.host", "set-host", "jira_host", "https://jira.example.com",
                tooltip_key="settings.host_tip",
            )
            yield from self._text_row(
                "settings.token", "set-token", "jira_token", "Token", password=True,
                tooltip_key="settings.token_tip",
            )
            yield from self._text_row(
                "settings.email", "set-email", "email", "user@example.com",
                tooltip_key="settings.email_tip",
            )
            legacy_on = bool(self._settings.get("use_legacy_api", False))
            budget_raw = self._settings.get("budget_field", "")
            budget_value = "" if budget_raw is None else str(budget_raw)
            with Horizontal(classes="settings-row", id="budget-row"):
                yield from self._label_with_icon(t("settings.budget_field"), t("settings.budget_field_tip"))
                yield Input(value=budget_value, placeholder="customfield_36461", id="set-budget-field")
                detect_btn = Button(
                    t("settings.budget_detect"),
                    id="btn-detect-budget",
                    disabled=legacy_on,
                )
                detect_btn.tooltip = t("settings.budget_detect_tip")
                yield detect_btn
            with Horizontal(classes="settings-row"):
                yield from self._label_with_icon(t("settings.use_legacy_api_label"), t("settings.use_legacy_api_hint"))
                yield Checkbox(
                    t("settings.use_legacy_api"),
                    value=legacy_on,
                    id="set-use-legacy-api",
                )

        with TabPane(t("settings.tab_network"), id="settings-tab-network"), VerticalScroll():
            yield from self._text_row(
                "settings.proxy_url", "set-proxy-url", "proxy_url",
                "http://proxy.example.com:8080",
                tooltip_key="settings.proxy_url_tip",
            )
            yield Static(t("settings.proxy_hint"), classes="hint")

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
            yield from self._text_row(
                "settings.hourly_rate", "set-hourly-rate", "hourly_rate", "0",
                tooltip_key="settings.hourly_rate_tip",
            )
            yield from self._text_row(
                "settings.vat_rate", "set-vat-rate", "vat_rate", "19",
                tooltip_key="settings.vat_rate_tip",
            )
            year_value = self._settings.get("year", 0)
            year_str = str(year_value) if isinstance(year_value, int) and year_value > 0 else ""
            with Horizontal(classes="settings-row"):
                yield Label(t("settings.year"))
                yield Input(value=year_str, placeholder=str(date.today().year), id="set-year")
            yield from self._text_row("settings.vacation_days", "set-vacation-days", "vacation_days", "30")

    @on(Checkbox.Changed, "#set-use-legacy-api")
    def _on_legacy_changed(self, event: Checkbox.Changed) -> None:
        """Deaktiviert die Budget-Autoerkennung im Legacy-Modus."""
        self.query_one("#btn-detect-budget", Button).disabled = event.value

    @on(Button.Pressed, "#btn-detect-budget")
    def _on_detect_budget_pressed(self) -> None:
        """Startet die Budget-Feld-Autoerkennung (Cloud-Modus)."""
        self._detect_budget_field()

    @work(exclusive=True)
    async def _detect_budget_field(self) -> None:
        """Ermittelt das Budget-Custom-Field ueber /rest/api/3/field.

        Liest Host/Mail/Token aus den aktuellen Eingabefeldern (damit auch
        frisch eingetippte Werte greifen), sucht Custom-Fields mit "budget"
        im Namen und traegt den Treffer ins Budget-Feld ein.
        """
        host = self.query_one("#set-host", Input).value.strip()
        email = self.query_one("#set-email", Input).value.strip()
        token = self.query_one("#set-token", Input).value.strip()
        proxy = self.query_one("#set-proxy-url", Input).value.strip()

        if not host or not email or not token:
            self.notify(t("settings.budget_detect_need_creds"), severity="warning")
            return

        self.notify(t("settings.budget_detect_running"))
        client = JiraClient(host=host, email=email, token=token, legacy=False, proxy=proxy)

        try:
            matches = await client.detect_budget_field("budget")
        except JiraClientError as exc:
            self.notify(str(exc), severity="error")
            return
        except Exception as exc:  # noqa: BLE001 - jede Netzwerk-/Parse-Panne als Toast
            self.notify(str(exc), severity="error")
            return

        if not matches:
            self.notify(t("settings.budget_detect_none"), severity="warning")
            return

        field_id, field_name = matches[0]
        self.query_one("#set-budget-field", Input).value = field_id

        if len(matches) == 1:
            self.notify(t("settings.budget_detect_found", name=field_name, field=field_id))
        else:
            listing = ", ".join(f"{name} ({fid})" for fid, name in matches)
            self.notify(t("settings.budget_detect_multi", listing=listing), severity="warning")

    def _text_row(
        self,
        label_key: str,
        widget_id: str,
        settings_key: str,
        placeholder: str,
        password: bool = False,
        tooltip_key: str = "",
    ) -> ComposeResult:
        """Baut eine Label/Input-Zeile fuer ein Settings-Feld.

        Args:
            label_key:
                i18n-Key des Labels.
            widget_id:
                DOM-Id des Inputs.
            settings_key:
                Schluessel im Settings-Dict fuer den Vorgabewert.
            placeholder:
                Platzhaltertext.
            password:
                True maskiert die Eingabe.
            tooltip_key:
                Optionaler i18n-Key fuer einen Hover-Tooltip am Input.
        """
        raw = self._settings.get(settings_key, "")
        value = "" if raw is None else str(raw)
        with Horizontal(classes="settings-row"):
            if tooltip_key:
                yield from self._label_with_icon(t(label_key), t(tooltip_key))
            else:
                yield Label(t(label_key))
            yield Input(value=value, placeholder=placeholder, password=password, id=widget_id)

    def _label_with_icon(self, label_text: str, tip: str) -> ComposeResult:
        """Erzeugt Label + (?)-Hover-Tooltip-Icon in der Label-Spalte.

        Einheitliches Tooltip-Muster (analog console-error-scanner): ein
        ASCII-(?) neben dem Label, das beim Hover den Erklaerungstext zeigt.

        Args:
            label_text:
                Der Label-Text.
            tip:
                Der Tooltip-Text fuer das (?)-Icon.
        """
        with Horizontal(classes="label-with-icon"):
            yield Label(label_text)
            icon = Static(t("settings.info_icon"), classes="info-icon")
            icon.tooltip = tip
            yield icon

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
        settings["use_legacy_api"] = self.query_one("#set-use-legacy-api", Checkbox).value
        settings["proxy_url"] = self.query_one("#set-proxy-url", Input).value.strip()
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

        # MwSt-Satz in Prozent; Komma als Dezimaltrenner tolerieren (de-DE).
        vat_str = self.query_one("#set-vat-rate", Input).value.strip().replace(",", ".")
        settings["vat_rate"] = float(vat_str) if self._is_float(vat_str) else 19.0

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
