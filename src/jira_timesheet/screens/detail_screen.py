"""Ticket-Detail Modal Screen."""
from __future__ import annotations

from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Static

from jira_timesheet.models.timesheet import WorklogEntry


class DetailScreen(ModalScreen):
    """Modal-Dialog mit Ticket-Details."""

    DEFAULT_CSS = """
    DetailScreen {
        align: center middle;
    }

    DetailScreen > VerticalScroll {
        width: 80;
        height: auto;
        max-height: 28;
        background: $surface;
        border: thick $accent;
        padding: 1 2;
    }

    DetailScreen #detail-title {
        text-style: bold;
        margin-bottom: 1;
    }

    DetailScreen .detail-row {
        margin-bottom: 0;
    }

    DetailScreen .detail-label {
        color: $text-muted;
    }

    DetailScreen .detail-value {
        color: $text;
    }

    DetailScreen #detail-link {
        margin-top: 1;
    }

    DetailScreen #detail-footer {
        margin-top: 1;
        color: $text-muted;
        text-align: center;
    }
    """

    BINDINGS = [
        Binding("escape", "close", "Schliessen"),
        Binding("d", "close", "Schliessen", show=False),
    ]

    def __init__(self, entry: WorklogEntry, jira_host: str = "", **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._entry = entry
        self._jira_host = jira_host.rstrip("/")

    def compose(self) -> ComposeResult:
        """Erstellt den Detail-Dialog."""
        e = self._entry

        with VerticalScroll():
            yield Static(f"{e.ticket} — {e.summary}", id="detail-title")

            yield Static(f"  Datum:             {e.date:%d.%m.%Y}", classes="detail-row")
            yield Static(f"  Stunden:           {e.hours:.2f}h", classes="detail-row")
            yield Static(f"  Autor:             {e.author}", classes="detail-row")

            if e.assignee:
                yield Static(f"  Bearbeiter:        {e.assignee}", classes="detail-row")

            yield Static("", classes="detail-row")

            if e.issuetype:
                yield Static(f"  Typ:               {e.issuetype}", classes="detail-row")
            if e.status:
                yield Static(f"  Status:            {e.status}", classes="detail-row")
            if e.resolution:
                yield Static(f"  Loesung:           {e.resolution}", classes="detail-row")
            if e.priority:
                yield Static(f"  Prioritaet:        {e.priority}", classes="detail-row")

            yield Static("", classes="detail-row")

            if e.budget:
                yield Static(f"  Budget:            {e.budget}", classes="detail-row")
            if e.components:
                yield Static(f"  Komponenten:       {e.components}", classes="detail-row")
            if e.labels:
                yield Static(f"  Labels:            {e.labels}", classes="detail-row")

            yield Static("", classes="detail-row")

            if e.created:
                yield Static(f"  Erstellt:          {e.created}", classes="detail-row")
            if e.updated:
                yield Static(f"  Aktualisiert:      {e.updated}", classes="detail-row")
            if e.total_logged:
                yield Static(f"  Gesamt-Protokoll.: {e.total_logged}", classes="detail-row")

            if self._jira_host and e.ticket:
                url = f"{self._jira_host}/browse/{e.ticket}"
                yield Static(f"  [link={url}]{url}[/link]", id="detail-link", markup=True)

            yield Static("ESC = Schliessen", id="detail-footer")

    def action_close(self) -> None:
        """Schliesst den Dialog."""
        self.dismiss()
