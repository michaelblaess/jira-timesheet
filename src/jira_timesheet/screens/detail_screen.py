"""Ticket-Detail Modal Screen."""

from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Center, Vertical, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Static

from jira_timesheet.i18n import t
from jira_timesheet.models.timesheet import WorklogEntry

# Spaltenbreite fuer die Label-Ausrichtung (Label inkl. Doppelpunkt).
_LABEL_WIDTH = 20


class DetailScreen(ModalScreen):
    """Modal-Dialog mit Ticket-Details."""

    DEFAULT_CSS = """
    DetailScreen {
        align: center middle;
    }

    DetailScreen > Vertical {
        width: 80;
        height: auto;
        max-height: 30;
        background: $surface;
        border: thick $accent;
        padding: 1 2;
    }

    DetailScreen #detail-title {
        width: 1fr;
        height: auto;
        min-height: 3;
        content-align: center middle;
        text-align: center;
        text-style: bold;
        background: $accent;
        color: auto;
        margin-bottom: 1;
    }

    DetailScreen #detail-body {
        height: auto;
        max-height: 20;
    }

    DetailScreen .detail-row {
        margin-bottom: 0;
    }

    DetailScreen #detail-link {
        margin-top: 1;
    }

    DetailScreen #detail-footer {
        height: auto;
        margin-top: 1;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "ESC"),
        Binding("d,D", "close", "D", show=False),
    ]

    def __init__(self, entry: WorklogEntry, jira_host: str = "", **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._entry = entry
        self._jira_host = jira_host.rstrip("/")

    def compose(self) -> ComposeResult:
        """Erstellt den Detail-Dialog."""
        e = self._entry

        with Vertical():
            yield Static(f"{e.ticket} — {e.summary}", id="detail-title")

            with VerticalScroll(id="detail-body"):
                yield self._row("detail.date", f"{e.date:%d.%m.%Y}")
                yield self._row("detail.hours", f"{e.hours:.2f}h")
                yield self._row("detail.author", e.author)

                if e.assignee:
                    yield self._row("detail.assignee", e.assignee)

                yield Static("", classes="detail-row")

                if e.issuetype:
                    yield self._row("detail.type", e.issuetype)
                if e.status:
                    yield self._row("detail.status", e.status)
                if e.resolution:
                    yield self._row("detail.resolution", e.resolution)
                if e.priority:
                    yield self._row("detail.priority", e.priority)

                yield Static("", classes="detail-row")

                if e.budget:
                    yield self._row("detail.budget", e.budget)
                if e.components:
                    yield self._row("detail.components", e.components)
                if e.labels:
                    yield self._row("detail.labels", e.labels)

                yield Static("", classes="detail-row")

                if e.created:
                    yield self._row("detail.created", e.created)
                if e.updated:
                    yield self._row("detail.updated", e.updated)
                if e.total_logged:
                    yield self._row("detail.total_logged", e.total_logged)

                if self._jira_host and e.ticket:
                    from rich.text import Text

                    url = f"{self._jira_host}/browse/{e.ticket}"
                    link_text = Text(f"  {url}", style=f"link {url}")
                    yield Static(link_text, id="detail-link")

            with Center(id="detail-footer"):
                yield Button(t("common.close_button"), variant="primary", id="detail-close")

    @staticmethod
    def _row(label_key: str, value: object) -> Static:
        """Baut eine ausgerichtete Label/Wert-Zeile."""
        label = f"{t(label_key)}:"
        return Static(f"  {label:<{_LABEL_WIDTH}}{value}", classes="detail-row")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Schliesst den Dialog beim Klick auf den Close-Button."""
        self.dismiss()

    def action_close(self) -> None:
        """Schliesst den Dialog."""
        self.dismiss()
