"""Info / About Modal Screen."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Static

from jira_timesheet import __author__, __version__, __year__


class InfoScreen(ModalScreen):
    """Modal-Dialog mit Programm-Informationen."""

    DEFAULT_CSS = """
    InfoScreen {
        align: center middle;
    }

    InfoScreen > VerticalScroll {
        width: 55;
        height: auto;
        max-height: 20;
        background: $surface;
        border: thick $accent;
        padding: 1 2;
    }

    InfoScreen #info-title {
        text-style: bold;
        text-align: center;
        margin-bottom: 1;
    }

    InfoScreen #info-body {
        margin-bottom: 1;
    }

    InfoScreen #info-footer {
        color: $text-muted;
        text-align: center;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "Schliessen"),
        Binding("q", "close", "Schliessen", show=False),
        Binding("i", "close", "Schliessen", show=False),
    ]

    def compose(self) -> ComposeResult:
        """Erstellt den Info-Dialog."""
        with VerticalScroll():
            yield Static(f"Jira Timesheet v{__version__}", id="info-title")
            yield Static(
                f"Autor:    {__author__}\n"
                f"Jahr:     {__year__}\n"
                f"Lizenz:   Apache 2.0\n"
                f"\n"
                f"TUI-Anwendung zum Generieren von\n"
                f"Stundenzetteln aus Jira Worklogs.\n"
                f"\n"
                f'  "The time is always right\n'
                f'   to do what is right."\n'
                f"\n"
                f"        \u2014 Martin Luther King Jr.",
                id="info-body",
            )
            yield Static("ESC = Schliessen", id="info-footer")

    def action_close(self) -> None:
        """Schliesst den Dialog."""
        self.dismiss()
