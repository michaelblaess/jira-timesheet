"""Zusammenfassungs-Header: Soll/Ist/Differenz, Durchschnitt, Verdienst."""

from __future__ import annotations

from textual_widgets import InfoHeader, InfoItem

from jira_timesheet.i18n import t
from jira_timesheet.models.timesheet import Timesheet

_EMPTY = "—"
_KEYS = ("workdays", "actual", "target", "diff", "average", "net", "gross")


class SummaryPanel(InfoHeader):  # type: ignore[misc]
    """Einzeilige Kennzahlen: Arbeitstage, Ist, Soll, Diff, Ø, Netto, Brutto."""

    def __init__(self, **kwargs: object) -> None:
        self._timesheet: Timesheet | None = None
        self._target_hours: float = 0.0
        self._hourly_rate: float = 0.0

        items = [
            InfoItem(key="workdays", label=t("summary.workdays"), value=_EMPTY, value_style="dim"),
            InfoItem(key="actual", label=t("summary.actual"), value=_EMPTY, value_style="dim"),
            InfoItem(key="target", label=t("summary.target"), value=_EMPTY, value_style="dim"),
            InfoItem(key="diff", label=t("summary.diff"), value=_EMPTY, value_style="dim"),
            InfoItem(key="average", label=t("summary.average"), value=_EMPTY, value_style="dim"),
            InfoItem(key="net", label=t("summary.net"), value=_EMPTY, value_style="dim"),
            InfoItem(key="gross", label=t("summary.gross"), value=_EMPTY, value_style="dim"),
        ]
        super().__init__(items, columns=7, label_width=12, separator=" | ", **kwargs)

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

        self.set_value("workdays", str(timesheet.working_days), value_style="bold")
        self.set_value("actual", f"{timesheet.total_hours:.2f}h", value_style="bold")
        self.set_value("average", f"{timesheet.average_hours:.2f}", value_style="bold")

        if target_hours > 0:
            diff = timesheet.total_hours - target_hours
            diff_style = "bold red" if diff < 0 else "bold green"
            sign = "+" if diff >= 0 else ""
            self.set_value("target", f"{target_hours:.2f}h", value_style="bold")
            self.set_value("diff", f"{sign}{diff:.2f}h", value_style=diff_style)
        else:
            self.set_value("target", _EMPTY, value_style="dim")
            self.set_value("diff", _EMPTY, value_style="dim")

        if hourly_rate > 0:
            netto = timesheet.total_hours * hourly_rate
            brutto = netto * 1.19
            self.set_value("net", f"{netto:,.2f}€", value_style="bold")
            self.set_value("gross", f"{brutto:,.2f}€", value_style="bold")
        else:
            self.set_value("net", _EMPTY, value_style="dim")
            self.set_value("gross", _EMPTY, value_style="dim")

    def clear(self) -> None:
        """Setzt alle Werte auf den Platzhalter zurück."""
        self._timesheet = None
        self._target_hours = 0.0
        self._hourly_rate = 0.0
        for key in _KEYS:
            self.set_value(key, _EMPTY, value_style="dim")
