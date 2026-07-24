"""Rueckfrage-Dialog fuer destruktive Aktionen."""

from __future__ import annotations

from textual import on
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from jira_timesheet.i18n import t


class ConfirmScreen(ModalScreen[bool]):
    """Fragt vor einer destruktiven Aktion nach. Gibt True bei Bestaetigung."""

    DEFAULT_CSS = """
    ConfirmScreen {
        align: center middle;
    }

    ConfirmScreen > Vertical {
        width: auto;
        min-width: 50;
        max-width: 80;
        height: auto;
        background: $surface;
        border: thick $error;
        padding: 1 2;
    }

    ConfirmScreen #confirm-title {
        text-align: center;
        text-style: bold;
        color: $error;
        margin-bottom: 1;
    }

    ConfirmScreen #confirm-message {
        height: auto;
        padding: 0 1;
    }

    ConfirmScreen #confirm-buttons {
        height: 3;
        align: center middle;
        margin-top: 1;
    }

    ConfirmScreen #confirm-buttons Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        Binding("escape", "cancel", "Esc"),
    ]

    def __init__(self, message: str, title: str = "") -> None:
        super().__init__()
        self._message = message
        self._title = title or t("confirm.title")

    def compose(self) -> ComposeResult:
        """Baut Titel, Meldung und die beiden Buttons."""
        with Vertical():
            yield Static(self._title, id="confirm-title")
            yield Static(self._message, id="confirm-message")
            with Horizontal(id="confirm-buttons"):
                yield Button(t("common.btn_delete"), variant="error", id="confirm-ok")
                yield Button(t("common.btn_cancel_plain"), variant="default", id="confirm-cancel")

    def on_mount(self) -> None:
        """Fokus auf Abbrechen - versehentliches Enter loescht so nichts."""
        self.set_focus(self.query_one("#confirm-cancel", Button))

    @on(Button.Pressed, "#confirm-ok")
    def _on_ok(self) -> None:
        """Bestaetigt die Aktion."""
        self.dismiss(True)

    @on(Button.Pressed, "#confirm-cancel")
    def _on_cancel(self) -> None:
        """Bricht die Aktion ab."""
        self.dismiss(False)

    def action_cancel(self) -> None:
        """Esc bricht ab."""
        self.dismiss(False)
