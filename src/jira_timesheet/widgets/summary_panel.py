"""Zusammenfassungs-Widget fuer den Stundenzettel."""
from __future__ import annotations

from rich.text import Text
from textual.app import RenderResult
from textual.widget import Widget

from jira_timesheet.models.timesheet import Timesheet


class SummaryPanel(Widget):
    """Kompakte Zusammenfassung: Soll/Ist/Differenz, Arbeitstage, Durchschnitt."""

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
        self._target_hours: float = 0.0

    def update_timesheet(self, timesheet: Timesheet, target_hours: float = 0.0) -> None:
        """Aktualisiert die Zusammenfassung."""
        self._timesheet = timesheet
        self._target_hours = target_hours
        self.refresh()

    def clear(self) -> None:
        """Setzt die Anzeige zurueck."""
        self._timesheet = None
        self._target_hours = 0.0
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
        text.append("Ist: ", style="dim")
        text.append(f"{ts.total_hours:.2f}h", style="bold")

        if self._target_hours > 0:
            diff = ts.total_hours - self._target_hours
            text.append("  |  ", style="dim")
            text.append("Soll: ", style="dim")
            text.append(f"{self._target_hours:.2f}h", style="bold")
            text.append("  |  ", style="dim")

            diff_style = "bold red" if diff < 0 else "bold green"
            diff_sign = "+" if diff >= 0 else ""
            text.append(f"{diff_sign}{diff:.2f}h", style=diff_style)

        text.append("  |  ", style="dim")
        text.append("\u00d8 ", style="dim")
        text.append(f"{ts.average_hours:.2f}h/Tag", style="bold")

        return text
