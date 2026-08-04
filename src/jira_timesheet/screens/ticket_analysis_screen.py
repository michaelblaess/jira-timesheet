"""Eingabe-Dialog der Ticket-Analyse.

Fragt Ticket-Key oder Jira-Link ab und gibt den erkannten Key zurueck. Den
Abruf und das Speichern uebernimmt die Anwendung - der Screen bleibt reine
Eingabe.
"""

from __future__ import annotations

import re

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Static

from jira_timesheet.i18n import t

# Ticket-Keys lassen sich aus jedem Jira-Link ziehen - meist wird die volle
# URL aus dem Browser kopiert.
KEY_PATTERN = re.compile(r"([A-Z][A-Z0-9]+-\d+)")


def ticket_key(reference: str) -> str:
    """Zieht den Ticket-Key aus einem Key oder einer beliebigen Jira-URL.

    Args:
        reference:
            Key wie "ABC-123" oder ein Link darauf.

    Returns:
        Der erkannte Ticket-Key, oder ein leerer String.
    """
    match = KEY_PATTERN.search(reference.strip().upper())
    return match.group(1) if match else ""


class TicketAnalysisScreen(ModalScreen[str | None]):
    """Fragt das zu analysierende Ticket ab."""

    DEFAULT_CSS = """
    TicketAnalysisScreen {
        align: center middle;
    }

    TicketAnalysisScreen > Vertical {
        width: auto;
        min-width: 62;
        max-width: 90;
        height: auto;
        background: $surface;
        border: thick $accent;
        padding: 1 2;
    }

    TicketAnalysisScreen #ticket-title {
        text-align: center;
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    TicketAnalysisScreen #ticket-intro {
        height: auto;
        padding: 0 1;
        margin-bottom: 1;
    }

    TicketAnalysisScreen #ticket-input {
        margin-bottom: 1;
    }

    TicketAnalysisScreen #ticket-hint {
        height: auto;
        padding: 0 1;
        color: $text-muted;
    }

    TicketAnalysisScreen #ticket-buttons {
        height: 3;
        align: center middle;
        margin-top: 1;
    }

    TicketAnalysisScreen #ticket-buttons Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Esc"),
    ]

    def compose(self) -> ComposeResult:
        """Baut den Dialog."""
        with Vertical():
            yield Static(t("ticket_report.title"), id="ticket-title")
            yield Static(t("ticket_report.intro"), id="ticket-intro")
            yield Input(placeholder=t("ticket_report.placeholder"), id="ticket-input")
            yield Static("", id="ticket-hint")
            with Horizontal(id="ticket-buttons"):
                yield Button(t("ticket_report.btn_analyse"), variant="primary", id="ticket-ok")
                yield Button(t("common.btn_cancel"), id="ticket-cancel")

    def on_mount(self) -> None:
        """Setzt den Fokus ins Eingabefeld."""
        self.query_one("#ticket-input", Input).focus()

    @on(Input.Changed, "#ticket-input")
    def _on_changed(self, event: Input.Changed) -> None:
        """Zeigt den erkannten Key als Bestaetigung an."""
        key = ticket_key(event.value)
        hint = self.query_one("#ticket-hint", Static)
        hint.update(t("ticket_report.recognised", ticket=key) if key else "")
        self.query_one("#ticket-ok", Button).disabled = not key

    @on(Input.Submitted, "#ticket-input")
    def _on_submitted(self) -> None:
        """Enter im Eingabefeld startet die Analyse."""
        self._accept()

    @on(Button.Pressed, "#ticket-ok")
    def _on_ok(self) -> None:
        self._accept()

    @on(Button.Pressed, "#ticket-cancel")
    def _on_cancel(self) -> None:
        self.dismiss(None)

    def _accept(self) -> None:
        """Gibt den erkannten Key zurueck - ohne Key bleibt der Dialog offen."""
        key = ticket_key(self.query_one("#ticket-input", Input).value)
        if key:
            self.dismiss(key)

    def action_cancel(self) -> None:
        """Esc bricht ab."""
        self.dismiss(None)
