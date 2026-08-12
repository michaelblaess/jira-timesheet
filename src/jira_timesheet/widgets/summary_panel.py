"""Zusammenfassungs-Widget fuer den Stundenzettel."""

from __future__ import annotations

from typing import Any

from textual_widgets import StatusBar, StatusItem

from jira_timesheet.i18n import REDACTED_MONEY, format_eur, format_number, t
from jira_timesheet.models.settings import DEFAULT_MANUAL_COLOR
from jira_timesheet.models.timesheet import Timesheet


class SummaryPanel(StatusBar):  # type: ignore[misc]
    """Einzeilige Kennzahlen: Soll/Ist/Differenz, Durchschnitt, Verdienst.

    Rahmen und Trenner kommen aus der StatusBar in textual-widgets - damit
    sieht die Leiste in allen Anwendungen gleich aus. Der InfoHeader taugt
    dafuer weiterhin nicht: sein Spaltenraster mit fester ``label_width``
    spreizt Label und Wert auseinander.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(hint=t("summary.generate_hint"), **kwargs)
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
        self._aktualisieren()

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
        self._aktualisieren()

    def set_anonymized(self, value: bool) -> None:
        """Schaltet die Zensur der Geldbetraege ein/aus (Screenshot-Modus)."""
        self._anonymized = value
        self._aktualisieren()

    def show_items(self, items: list[StatusItem]) -> None:
        """Zeigt fremde Kennzahlen statt der Stundenzettel-Werte.

        Gedacht fuer die Ticket-Ansichten, die eigene Zahlen mitbringen. Der
        Stundenzettel bleibt gespeichert - ein Wechsel zurueck in die Liste
        stellt ihn ueber ``refresh_timesheet`` wieder her.

        Args:
            items:
                Die anzuzeigenden Eintraege. Leer zeigt den Hinweistext.
        """
        if not items:
            super().clear()
            return
        self.set_items(items)

    def refresh_timesheet(self) -> None:
        """Zeigt wieder die Kennzahlen des zuletzt geladenen Stundenzettels."""
        self._aktualisieren()

    def clear(self) -> None:
        """Setzt die Anzeige zurueck (zeigt den Generate-Hinweis)."""
        self._timesheet = None
        self._target_hours = 0.0
        self._hourly_rate = 0.0
        self._aktualisieren()

    def set_manual_marking(self, enabled: bool, color: str) -> None:
        """Uebernimmt die Markierungs-Einstellungen fuer den manuellen Anteil."""
        self._mark_manual = enabled
        self._manual_color = color
        self._aktualisieren()

    def _manual_style(self) -> str:
        """Rich-Style fuer den manuellen Stundenanteil."""
        return f"bold #{self._manual_color}" if self._mark_manual else "bold"

    def _aktualisieren(self) -> None:
        """Traegt die Kennzahlen in die Leiste ein.

        NICHT ``_redraw`` nennen — so heisst die interne Methode der
        StatusBar. Ein Override davon fuehrt in eine Endlosschleife, weil
        ``set_items``/``clear`` genau sie aufrufen. (``_render`` ist aus dem
        gleichen Grund tabu: das gehoert Textual selbst.)
        """
        if self._timesheet is None:
            # super(), nicht self: die eigene clear() setzt den Zustand
            # zurueck und ruft wieder hierher - das waere eine Endlosschleife.
            super().clear()
            return
        self.set_items(self._build_items())

    def _build_items(self) -> list[StatusItem]:
        """Stellt die Kennzahlen als Eintraege der Statusleiste zusammen."""
        assert self._timesheet is not None
        ts = self._timesheet
        items = [
            StatusItem(t("summary.workdays"), str(ts.working_days)),
            StatusItem(t("summary.actual"), f"{format_number(ts.total_hours)}h"),
        ]

        # Manueller Anteil nur zeigen, wenn es welchen gibt - sonst bliebe eine
        # "0,00h"-Zelle stehen, die nichts aussagt.
        manual_hours = sum(e.hours for e in ts.all_entries if e.manual)
        if manual_hours > 0:
            items.append(
                StatusItem(
                    t("summary.manual"),
                    f"{format_number(manual_hours)}h",
                    value_style=self._manual_style(),
                )
            )

        if self._target_hours > 0:
            items.append(StatusItem(t("summary.target"), f"{format_number(self._target_hours)}h"))
            diff = ts.total_hours - self._target_hours
            sign = "+" if diff >= 0 else ""
            items.append(
                StatusItem(
                    "",
                    f"{sign}{format_number(diff)}h",
                    value_style="bold red" if diff < 0 else "bold green",
                )
            )

        # Ohne Beschriftung: das Zeichen selbst ist die Beschriftung.
        items.append(StatusItem("", f"Ø {format_number(ts.average_hours)}{t('summary.avg_suffix')}"))

        if self._hourly_rate > 0:
            netto = ts.total_hours * self._hourly_rate
            brutto = netto * (1.0 + self._vat_rate / 100.0)
            items.append(
                StatusItem(
                    t("summary.net"),
                    REDACTED_MONEY if self._anonymized else format_eur(netto),
                )
            )
            items.append(
                StatusItem(
                    t("summary.gross"),
                    REDACTED_MONEY if self._anonymized else format_eur(brutto),
                )
            )
        return items
