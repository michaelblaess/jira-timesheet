"""Settings Modal Screen."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Checkbox, Input, Label, Select, Static


from jira_timesheet.models.settings import Settings
from jira_timesheet.services.holiday_service import FEDERAL_STATES

_STATE_OPTIONS = [(f"{name} ({code})", code) for code, name in sorted(FEDERAL_STATES.items(), key=lambda x: x[1])]


class SettingsScreen(ModalScreen[bool | None]):
    """Modal-Dialog fuer Benutzereinstellungen."""

    DEFAULT_CSS = """
    SettingsScreen {
        align: center middle;
    }

    SettingsScreen > VerticalScroll {
        width: 70;
        height: auto;
        max-height: 40;
        background: $surface;
        border: thick $accent;
        padding: 1 2;
    }

    SettingsScreen #settings-title {
        text-style: bold;
        margin-bottom: 1;
    }

    SettingsScreen Label {
        margin-top: 1;
        color: $text-muted;
    }

    SettingsScreen Input {
        margin-bottom: 0;
    }

    SettingsScreen Select {
        margin-bottom: 0;
    }

    SettingsScreen #settings-footer {
        margin-top: 1;
        height: 3;
        align: center middle;
    }

    SettingsScreen #btn-save {
        margin-right: 2;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Abbrechen"),
        Binding("ctrl+s", "save", "Speichern"),
    ]

    def __init__(self, settings: Settings, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._settings = settings

    def compose(self) -> ComposeResult:
        """Erstellt das Settings-Formular."""
        with VerticalScroll():
            yield Static("Einstellungen", id="settings-title")

            yield Label("Jira Host URL:")
            yield Input(
                value=self._settings.jira_host,
                placeholder="https://jira.example.com",
                id="input-host",
            )

            yield Label("Jira Bearer Token:")
            yield Input(
                value=self._settings.jira_token,
                placeholder="Token hier einfuegen",
                password=True,
                id="input-token",
            )

            yield Label("E-Mail (Jira Username):")
            yield Input(
                value=self._settings.email,
                placeholder="user@example.com",
                id="input-email",
            )

            yield Label("Logo-Pfad (fuer Excel/PDF Export):")
            yield Input(
                value=self._settings.logo_path,
                placeholder="Leer = Default-Logo aus assets/",
                id="input-logo",
            )

            yield Label("Budget Custom Field ID:")
            yield Input(
                value=self._settings.budget_field,
                placeholder="customfield_36461",
                id="input-budget-field",
            )

            yield Label("Bundesland (Feiertage):")
            yield Select(
                options=_STATE_OPTIONS,
                value=self._settings.federal_state,
                id="select-federal-state",
            )

            yield Label("Soll-Stunden pro Tag:")
            yield Input(
                value=str(self._settings.hours_per_day),
                placeholder="8.0",
                id="input-hours-per-day",
            )

            yield Label("Max. Jahresstunden:")
            yield Input(
                value=str(self._settings.max_yearly_hours),
                placeholder="1720.0",
                id="input-max-yearly",
            )

            yield Checkbox(
                "Soll-Stunden im Excel/PDF Export anzeigen",
                value=self._settings.show_target_hours_in_export,
                id="check-target-export",
            )

            with Horizontal(id="settings-footer"):
                yield Button("Speichern", id="btn-save", variant="primary")
                yield Button("Abbrechen", id="btn-cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Reagiert auf Button-Klicks."""
        if event.button.id == "btn-save":
            self.action_save()
        elif event.button.id == "btn-cancel":
            self.action_cancel()

    def action_save(self) -> None:
        """Speichert die Settings und schliesst den Dialog."""
        self._settings.jira_host = self.query_one("#input-host", Input).value.strip()
        self._settings.jira_token = self.query_one("#input-token", Input).value.strip()
        self._settings.email = self.query_one("#input-email", Input).value.strip()
        self._settings.logo_path = self.query_one("#input-logo", Input).value.strip()
        self._settings.budget_field = self.query_one("#input-budget-field", Input).value.strip()
        state_select = self.query_one("#select-federal-state", Select)
        self._settings.federal_state = str(state_select.value) if state_select.value != Select.BLANK else self._settings.federal_state
        try:
            self._settings.hours_per_day = float(self.query_one("#input-hours-per-day", Input).value.strip())
        except ValueError:
            pass
        try:
            self._settings.max_yearly_hours = float(self.query_one("#input-max-yearly", Input).value.strip())
        except ValueError:
            pass
        self._settings.show_target_hours_in_export = self.query_one("#check-target-export", Checkbox).value
        self.dismiss(True)

    def action_cancel(self) -> None:
        """Schliesst den Dialog ohne Speichern."""
        self.dismiss(None)
