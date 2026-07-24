"""Dialog zum Anlegen und Bearbeiten manuell erfasster Zeiten."""

from __future__ import annotations

import contextlib
from dataclasses import dataclass
from datetime import date

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Label, Select, Static
from textual_widgets import DatePickerScreen

from jira_timesheet.i18n import t
from jira_timesheet.services.duration import format_hours, parse_hours
from jira_timesheet.services.manual_entry_service import ManualEntry


@dataclass
class ManualEntryResult:
    """Ergebnis des Dialogs: der Eintrag und was damit passieren soll."""

    entry: ManualEntry
    delete: bool = False


class ManualEntryScreen(ModalScreen[ManualEntryResult | None]):
    """Erfasst einen manuellen Zeiteintrag. Gibt None bei Abbruch zurueck."""

    DEFAULT_CSS = """
    ManualEntryScreen {
        align: center middle;
    }

    ManualEntryScreen > Vertical {
        width: 80;
        max-width: 90%;
        height: auto;
        max-height: 90%;
        background: $surface;
        border: thick $accent;
        padding: 1 2;
    }

    ManualEntryScreen #manual-title {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    ManualEntryScreen #manual-fields {
        height: auto;
        max-height: 90%;
    }

    ManualEntryScreen .manual-row {
        height: 3;
    }

    ManualEntryScreen .manual-row Label {
        width: 16;
        padding: 1 1;
    }

    ManualEntryScreen .manual-row Input,
    ManualEntryScreen .manual-row Select {
        width: 1fr;
    }

    ManualEntryScreen #manual-date-row Button {
        width: auto;
        margin-left: 1;
    }

    ManualEntryScreen #manual-error {
        color: $error;
        height: auto;
        padding: 0 1;
    }

    ManualEntryScreen #manual-buttons {
        dock: bottom;
        height: 3;
        align: center middle;
        margin-top: 1;
    }

    ManualEntryScreen #manual-buttons Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Esc"),
        Binding("ctrl+s", "save", "Ctrl+S"),
    ]

    def __init__(
        self,
        entry: ManualEntry | None = None,
        default_date: date | None = None,
        default_customer: str = "",
        customers: list[str] | None = None,
    ) -> None:
        super().__init__()
        self._entry = entry
        self._is_edit = entry is not None
        self._customers = list(customers or [])
        if entry is not None:
            self._date = entry.entry_date
            self._ticket = entry.ticket
            self._summary = entry.summary
            self._customer = entry.customer or default_customer
            self._hours_text = format_hours(entry.hours)
        else:
            self._date = default_date or date.today()
            self._ticket = ""
            self._summary = ""
            self._customer = default_customer
            self._hours_text = ""

    def compose(self) -> ComposeResult:
        """Baut Titel, Eingabefelder und Buttonleiste."""
        title = t("manual.title_edit") if self._is_edit else t("manual.title_new")
        with Vertical():
            yield Static(title, id="manual-title")
            with VerticalScroll(id="manual-fields"):
                with Horizontal(classes="manual-row", id="manual-date-row"):
                    yield Label(t("manual.date"))
                    yield Input(value=f"{self._date:%d.%m.%Y}", placeholder="TT.MM.JJJJ", id="manual-date")
                    yield Button(t("manual.pick_date"), id="manual-pick-date")
                with Horizontal(classes="manual-row"):
                    yield Label(t("manual.ticket"))
                    yield Input(value=self._ticket, id="manual-ticket")
                with Horizontal(classes="manual-row"):
                    yield Label(t("manual.summary"))
                    yield Input(value=self._summary, placeholder=t("manual.summary_ph"), id="manual-summary")
                with Horizontal(classes="manual-row"):
                    yield Label(t("manual.customer"))
                    yield Select(
                        options=[(name, name) for name in self._customer_options()],
                        # Select.NULL ist der Sentinel fuer "nichts gewaehlt".
                        # Select.BLANK gibt es nicht - es loest zu False auf und
                        # laesst den Dialog mit InvalidSelectValueError abstuerzen.
                        value=self._customer if self._customer else Select.NULL,
                        allow_blank=True,
                        id="manual-customer",
                    )
                with Horizontal(classes="manual-row"):
                    yield Label(t("manual.hours"))
                    yield Input(value=self._hours_text, placeholder=t("manual.hours_ph"), id="manual-hours")
                yield Static("", id="manual-error")
            with Horizontal(id="manual-buttons"):
                yield Button(t("common.btn_save"), variant="primary", id="manual-save")
                # Loeschen gibt es nur beim Bearbeiten - beim Anlegen waere es sinnlos.
                if self._is_edit:
                    yield Button(t("common.btn_delete"), variant="error", id="manual-delete")
                yield Button(t("common.btn_cancel"), variant="default", id="manual-cancel")

    def on_mount(self) -> None:
        """Setzt den Fokus auf das erste sinnvoll zu fuellende Feld."""
        target = "manual-ticket" if not self._is_edit else "manual-date"
        with contextlib.suppress(Exception):
            self.set_focus(self.query_one(f"#{target}", Input))

    # --- Aktionen ---------------------------------------------------

    @on(Button.Pressed, "#manual-save")
    def _on_save_pressed(self) -> None:
        """Speichern-Button."""
        self.action_save()

    @on(Button.Pressed, "#manual-cancel")
    def _on_cancel_pressed(self) -> None:
        """Abbrechen-Button."""
        self.action_cancel()

    @on(Button.Pressed, "#manual-delete")
    def _on_delete_pressed(self) -> None:
        """Loeschen-Button - die Rueckfrage stellt der Host."""
        if self._entry is None:
            return
        self.dismiss(ManualEntryResult(entry=self._entry, delete=True))

    @on(Button.Pressed, "#manual-pick-date")
    def _on_pick_date_pressed(self) -> None:
        """Oeffnet den Kalender zur Datumsauswahl."""
        current = self._read_date() or date.today()
        self.app.push_screen(
            DatePickerScreen(initial_date=current.isoformat()),
            callback=self._on_date_picked,
        )

    def _on_date_picked(self, selected: str | None) -> None:
        """Uebernimmt das im Kalender gewaehlte Datum."""
        if not selected:
            return
        with contextlib.suppress(ValueError):
            picked = date.fromisoformat(selected)
            self.query_one("#manual-date", Input).value = f"{picked:%d.%m.%Y}"

    def action_cancel(self) -> None:
        """Bricht ab, ohne zu speichern."""
        self.dismiss(None)

    def action_save(self) -> None:
        """Validiert die Eingaben und gibt den Eintrag zurueck."""
        entry_date = self._read_date()
        if entry_date is None:
            self._show_error(t("manual.err_date"))
            return

        hours = parse_hours(self.query_one("#manual-hours", Input).value)
        if hours is None or hours <= 0:
            self._show_error(t("manual.err_hours"))
            return

        ticket = self.query_one("#manual-ticket", Input).value.strip()
        summary = self.query_one("#manual-summary", Input).value.strip()
        if not ticket and not summary:
            self._show_error(t("manual.err_ticket_or_summary"))
            return

        self.dismiss(
            ManualEntryResult(
                entry=ManualEntry(
                    entry_id=self._entry.entry_id if self._entry is not None else 0,
                    entry_date=entry_date,
                    ticket=ticket,
                    summary=summary,
                    customer=self._selected_customer(),
                    hours=hours,
                )
            )
        )

    # --- Interna ----------------------------------------------------

    def _customer_options(self) -> list[str]:
        """Auswahlliste inklusive des aktuell gesetzten Kunden.

        Ein Eintrag, dessen Kunde inzwischen aus der Liste geflogen ist, darf
        seinen Wert beim Bearbeiten nicht stillschweigend verlieren.
        """
        options = list(self._customers)
        if self._customer and self._customer not in options:
            options.insert(0, self._customer)
        return options

    def _selected_customer(self) -> str:
        """Liest den gewaehlten Kunden; leere Auswahl ergibt einen leeren String."""
        value = self.query_one("#manual-customer", Select).value
        return str(value) if isinstance(value, str) else ""

    def _read_date(self) -> date | None:
        """Liest das Datumsfeld. Akzeptiert TT.MM.JJJJ und ISO."""
        raw = self.query_one("#manual-date", Input).value.strip()
        if not raw:
            return None
        for parser in (self._parse_german_date, date.fromisoformat):
            try:
                return parser(raw)
            except ValueError:
                continue
        return None

    @staticmethod
    def _parse_german_date(raw: str) -> date:
        """Parst TT.MM.JJJJ. Wirft ValueError bei ungueltiger Eingabe."""
        parts = raw.split(".")
        if len(parts) != 3:
            raise ValueError(f"Kein deutsches Datum: {raw}")
        day, month, year = (int(p) for p in parts)
        return date(year, month, day)

    def _show_error(self, message: str) -> None:
        """Zeigt eine Fehlermeldung unter den Feldern an."""
        with contextlib.suppress(Exception):
            self.query_one("#manual-error", Static).update(message)
