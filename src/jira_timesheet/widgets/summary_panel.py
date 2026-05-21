"""Zusammenfassungs-Widget fuer den Stundenzettel."""

from __future__ import annotations

from rich.text import Text
from textual.widgets import Static

from jira_timesheet.i18n import t
from jira_timesheet.models.timesheet import Timesheet


class SummaryPanel(Static):
    """Einzeilige Kennzahlen: Soll/Ist/Differenz, Durchschnitt, Verdienst.

    Static statt InfoHeader — eine fixe Inline-Stats-Zeile mit Pipe-Trennern
    laesst sich mit dem InfoHeader-Spaltenraster nicht kompakt rendern (die
    feste ``label_width`` spreizt Label und Wert auseinander). Static gibt
    die volle Kontrolle ueber Spacing und Doppelpunkte.
    """

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
        super().__init__("", **kwargs)
        self._timesheet: Timesheet | None = None
        self._target_hours: float = 0.0
        self._hourly_rate: float = 0.0

    def on_mount(self) -> None:
        """Setzt den initialen Hinweistext."""
        self._redraw()

    def update_timesheet(
        self,
        timesheet: Timesheet,
        target_hours: float = 0.0,
        hourly_rate: float = 0.0,
    ) -> None:
        """Aktualisiert die Werte aus einem geladenen Timesheet."""
        self._timesheet = timesheet
        self._target_hours = target_hours
        self._hourly_rate = hourly_rate
        self._redraw()

    def clear(self) -> None:
        """Setzt die Anzeige zurueck (zeigt den Generate-Hinweis)."""
        self._timesheet = None
        self._target_hours = 0.0
        self._hourly_rate = 0.0
        self._redraw()

    def _redraw(self) -> None:
        """Baut den aktuellen Inhalt und schreibt ihn ins Widget.

        NICHT ``_render`` nennen — das ist eine interne Textual-Widget-API,
        ein Override mit ``-> None`` crasht das Layout-System.
        """
        if self._timesheet is None:
            self.update(Text(t("summary.generate_hint"), style="dim"))
            return
        self.update(self._build_stats_text())

    def _build_stats_text(self) -> Text:
        """Erzeugt die Stats-Zeile als Rich Text."""
        assert self._timesheet is not None
        ts = self._timesheet
        text = Text()
        sep = "  |  "

        text.append("  ")
        text.append(f"{t('summary.workdays')}: ", style="dim")
        text.append(str(ts.working_days), style="bold")

        text.append(sep, style="dim")
        text.append(f"{t('summary.actual')}: ", style="dim")
        text.append(f"{ts.total_hours:.2f}h", style="bold")

        if self._target_hours > 0:
            text.append(sep, style="dim")
            text.append(f"{t('summary.target')}: ", style="dim")
            text.append(f"{self._target_hours:.2f}h", style="bold")

            text.append(sep, style="dim")
            diff = ts.total_hours - self._target_hours
            diff_style = "bold red" if diff < 0 else "bold green"
            sign = "+" if diff >= 0 else ""
            text.append(f"{sign}{diff:.2f}h", style=diff_style)

        text.append(sep, style="dim")
        text.append("Ø ", style="dim")
        text.append(f"{ts.average_hours:.2f}{t('summary.avg_suffix')}", style="bold")

        if self._hourly_rate > 0:
            netto = ts.total_hours * self._hourly_rate
            brutto = netto * 1.19
            text.append(sep, style="dim")
            text.append(f"{t('summary.net')}: ", style="dim")
            text.append(f"{netto:,.2f}€", style="bold")

            text.append(sep, style="dim")
            text.append(f"{t('summary.gross')}: ", style="dim")
            text.append(f"{brutto:,.2f}€", style="bold")

        return text
