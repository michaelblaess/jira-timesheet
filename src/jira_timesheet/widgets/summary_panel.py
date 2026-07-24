"""Zusammenfassungs-Widget fuer den Stundenzettel."""

from __future__ import annotations

from typing import Any

from rich.text import Text
from textual.widgets import Static

from jira_timesheet.i18n import format_eur, format_number, t
from jira_timesheet.models.settings import DEFAULT_MANUAL_COLOR
from jira_timesheet.models.timesheet import Timesheet

# Maske fuer zensierte Geldbetraege im Anonymisierungs-Modus (Screenshots).
_REDACTED = "••••• €"


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

    def __init__(self, **kwargs: Any) -> None:
        super().__init__("", **kwargs)
        self._timesheet: Timesheet | None = None
        self._target_hours: float = 0.0
        self._hourly_rate: float = 0.0
        self._vat_rate: float = 19.0
        # Anonymisierungs-Modus: zensiert Geldbetraege fuer Screenshots.
        self._anonymized: bool = False
        # Markierung des manuellen Anteils - gleiche Einstellung wie die Tabelle.
        self._mark_manual: bool = True
        self._manual_color: str = DEFAULT_MANUAL_COLOR

    def on_mount(self) -> None:
        """Setzt den initialen Hinweistext."""
        self._redraw()

    def update_timesheet(
        self,
        timesheet: Timesheet,
        target_hours: float = 0.0,
        hourly_rate: float = 0.0,
        vat_rate: float = 19.0,
    ) -> None:
        """Aktualisiert die Werte aus einem geladenen Timesheet."""
        self._timesheet = timesheet
        self._target_hours = target_hours
        self._hourly_rate = hourly_rate
        self._vat_rate = vat_rate
        # Frisch geladene (echte) Daten -> Geldbetraege wieder anzeigen.
        self._anonymized = False
        self._redraw()

    def set_anonymized(self, value: bool) -> None:
        """Schaltet die Zensur der Geldbetraege ein/aus (Screenshot-Modus)."""
        self._anonymized = value
        self._redraw()

    def clear(self) -> None:
        """Setzt die Anzeige zurueck (zeigt den Generate-Hinweis)."""
        self._timesheet = None
        self._target_hours = 0.0
        self._hourly_rate = 0.0
        self._redraw()

    def set_manual_marking(self, enabled: bool, color: str) -> None:
        """Uebernimmt die Markierungs-Einstellungen fuer den manuellen Anteil."""
        self._mark_manual = enabled
        self._manual_color = color
        self._redraw()

    def _manual_style(self) -> str:
        """Rich-Style fuer den manuellen Stundenanteil."""
        return f"bold #{self._manual_color}" if self._mark_manual else "bold"

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
        text.append(f"{format_number(ts.total_hours)}h", style="bold")

        # Manueller Anteil nur zeigen, wenn es welchen gibt - sonst bliebe eine
        # "0,00h"-Zelle stehen, die nichts aussagt.
        manual_hours = sum(e.hours for e in ts.all_entries if e.manual)
        if manual_hours > 0:
            text.append(sep, style="dim")
            text.append(f"{t('summary.manual')}: ", style="dim")
            text.append(f"{format_number(manual_hours)}h", style=self._manual_style())

        if self._target_hours > 0:
            text.append(sep, style="dim")
            text.append(f"{t('summary.target')}: ", style="dim")
            text.append(f"{format_number(self._target_hours)}h", style="bold")

            text.append(sep, style="dim")
            diff = ts.total_hours - self._target_hours
            diff_style = "bold red" if diff < 0 else "bold green"
            sign = "+" if diff >= 0 else ""
            text.append(f"{sign}{format_number(diff)}h", style=diff_style)

        text.append(sep, style="dim")
        text.append("Ø ", style="dim")
        text.append(f"{format_number(ts.average_hours)}{t('summary.avg_suffix')}", style="bold")

        if self._hourly_rate > 0:
            netto = ts.total_hours * self._hourly_rate
            brutto = netto * (1.0 + self._vat_rate / 100.0)
            netto_str = _REDACTED if self._anonymized else format_eur(netto)
            brutto_str = _REDACTED if self._anonymized else format_eur(brutto)
            text.append(sep, style="dim")
            text.append(f"{t('summary.net')}: ", style="dim")
            text.append(netto_str, style="bold")

            text.append(sep, style="dim")
            text.append(f"{t('summary.gross')}: ", style="dim")
            text.append(brutto_str, style="bold")

        return text
