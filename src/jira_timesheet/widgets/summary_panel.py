"""Zusammenfassungs-Widget fuer den Stundenzettel."""
from __future__ import annotations

from rich.text import Text
from textual.app import RenderResult
from textual.widget import Widget

from jira_timesheet.models.timesheet import Timesheet


class SummaryPanel(Widget):
    """Kompakte Zusammenfassung: Arbeitstage, Gesamtstunden, Durchschnitt."""

    DEFAULT_CSS = """
    SummaryPanel {
        height: auto;
        min-height: 1;
        padding: 0 1;
        background: $surface;
        border: solid $accent;
    }
    """

    def __init__(self, **kwargs: object) -> None:
        super().__init__(**kwargs)
        self._timesheet: Timesheet | None = None

    def update_timesheet(self, timesheet: Timesheet) -> None:
        """Aktualisiert die Zusammenfassung."""
        self._timesheet = timesheet
        self.refresh()

    def clear(self) -> None:
        """Setzt die Anzeige zurueck."""
        self._timesheet = None
        self.refresh()

    def render(self) -> RenderResult:
        """Rendert die Zusammenfassung."""
        if self._timesheet is None:
            return Text("  Druecke [G] um den Stundenzettel zu generieren", style="dim")

        ts = self._timesheet
        text = Text()
        text.append("  Arbeitstage: ", style="dim")
        text.append(str(ts.working_days), style="bold")
        text.append("  |  ", style="dim")
        text.append("Gesamt: ", style="dim")
        text.append(f"{ts.total_hours:.2f}h", style="bold")
        text.append("  |  ", style="dim")
        text.append("Ø ", style="dim")
        text.append(f"{ts.average_hours:.2f}h/Tag", style="bold")
        return text
