"""Jahresansicht als Reiter: zwoelf Monatskacheln, Jahressumme und Forecast.

War bis v1.19.0 ein Modal-Screen, der ueber die Taste "j" geoeffnet wurde und
seine Zahlen fertig im Konstruktor bekam. Als Dauer-Reiter muss dasselbe
Widget nachladbar sein - deshalb steht hier ``set_year`` statt eines
Konstruktor-Arguments, und die zwoelf Kacheln werden einmal aufgebaut und
danach nur noch befuellt (kein Ab- und Anmontieren beim Aktualisieren).
"""

from __future__ import annotations

from datetime import date
from typing import Any

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widget import Widget
from textual.widgets import Static

from jira_timesheet.i18n import REDACTED_MONEY, format_eur, format_number, t
from jira_timesheet.models.settings import DEFAULT_MANUAL_COLOR

_QUARTER_NAMES = ["Q1", "Q2", "Q3", "Q4"]


class MonthTile(Widget):
    """Einzelne Monatskachel."""

    DEFAULT_CSS = """
    MonthTile {
        width: 1fr;
        height: 100%;
        min-height: 6;
        padding: 0 1;
        border: solid $surface-lighten-2;
    }

    MonthTile.current {
        border: solid $accent;
    }
    """

    def __init__(
        self,
        month: int,
        year: int,
        actual_hours: float = 0.0,
        target_hours: float = 0.0,
        working_days: int = 0,
        target_days: int = 0,
        manual_hours: float = 0.0,
        mark_manual: bool = True,
        manual_color: str = DEFAULT_MANUAL_COLOR,
        **kwargs: Any,
    ) -> None:
        super().__init__(**kwargs)
        self._month = month
        self._year = year
        self._actual = actual_hours
        self._target = target_hours
        self._working_days = working_days
        self._target_days = target_days
        self._manual = manual_hours
        self._mark_manual = mark_manual
        self._manual_color = manual_color

    def on_mount(self) -> None:
        """CSS-Klassen setzen."""
        self._mark_current()

    def update_data(
        self,
        year: int,
        actual_hours: float,
        target_hours: float,
        working_days: int,
        target_days: int,
        manual_hours: float,
        mark_manual: bool,
        manual_color: str,
    ) -> None:
        """Uebernimmt neue Zahlen in eine bereits montierte Kachel.

        Ersetzt das frueher uebliche Neu-Erzeugen der Kachel: der Reiter bleibt
        stehen und wird nur befuellt, ein Jahreswechsel muss deshalb auch die
        Markierung des laufenden Monats nachziehen.

        Args:
            year:
                Jahr, zu dem die Kachel gehoert.
            actual_hours:
                Gebuchte Stunden des Monats.
            target_hours:
                Sollstunden des Monats.
            working_days:
                Tage mit Buchung.
            target_days:
                Arbeitstage des Monats.
            manual_hours:
                Davon manuell erfasst.
            mark_manual:
                Ob der manuelle Anteil farbig markiert wird.
            manual_color:
                Farbe der Markierung (Hex ohne Raute).
        """
        self._year = year
        self._actual = actual_hours
        self._target = target_hours
        self._working_days = working_days
        self._target_days = target_days
        self._manual = manual_hours
        self._mark_manual = mark_manual
        self._manual_color = manual_color
        self._mark_current()
        self.refresh()

    def _mark_current(self) -> None:
        """Hebt die Kachel des laufenden Monats hervor - und nur diese."""
        today = date.today()
        self.set_class(self._month == today.month and self._year == today.year, "current")

    def render(self) -> Text:
        """Rendert die Monatskachel mit Mini-Progressbar."""
        text = Text()
        name = t(f"month.{self._month}")

        if self._actual > 0 and self._target > 0:
            pct = min(self._actual / self._target * 100, 100)
            if pct >= 95:
                bar_style = "green"
                pct_style = "bold green"
            elif pct >= 70:
                bar_style = "yellow"
                pct_style = "bold yellow"
            else:
                bar_style = "red"
                pct_style = "bold red"

            text.append(f"{name}", style="bold")
            text.append(f"  {pct:.0f}%\n", style=pct_style)

            # Mini-Progressbar
            bar_len = 18
            filled = int(pct / 100 * bar_len)
            text.append("█" * filled, style=bar_style)
            text.append("░" * (bar_len - filled), style="dim")
            text.append("\n")

            text.append(f"{format_number(self._actual, 1)}h", style=pct_style)
            text.append(f" / {format_number(self._target, 0)}h\n", style="dim")

            days = t("year.month_days", days=self._working_days, target=self._target_days)
            text.append(f"▸ {days}", style="dim")
            self._append_manual(text)

        elif self._actual > 0:
            text.append(f"{name}\n", style="bold")
            text.append(f"{format_number(self._actual, 1)}h\n", style="bold yellow")
            text.append(f"▸ {t('year.month_days_single', days=self._working_days)}", style="dim")
            self._append_manual(text)

        elif self._target > 0:
            text.append(f"{name}\n", style="dim")
            text.append("░" * 18 + "\n", style="dim")
            text.append(f"{t('year.month_target', hours=format_number(self._target, 0))}\n", style="dim")
            text.append(f"▸ {t('year.month_days_single', days=self._target_days)}", style="dim")

        else:
            text.append(f"{name}\n", style="dim")
            text.append("—", style="dim")

        return text

    def _append_manual(self, text: Text) -> None:
        """Haengt den manuell erfassten Anteil an - nur wenn es einen gibt."""
        if self._manual <= 0:
            return
        style = f"bold #{self._manual_color}" if self._mark_manual else "bold"
        text.append("\n▸ ", style="dim")
        text.append(t("year.month_manual", hours=format_number(self._manual)), style=style)


class QuarterRow(Horizontal):
    """Quartalsreihe mit Label + 3 Monatskacheln."""

    DEFAULT_CSS = """
    QuarterRow {
        width: 100%;
        height: 1fr;
        min-height: 6;
    }

    QuarterRow .quarter-label {
        width: 4;
        height: 100%;
        padding: 1 0;
        text-style: bold;
        color: $text-muted;
    }
    """


class YearPanel(Vertical):
    """Der Reiter "Jahresansicht": Kachelraster, Jahressumme und Forecast."""

    DEFAULT_CSS = """
    YearPanel {
        height: 1fr;
        padding: 0 1;
        overflow: hidden;
    }

    /* Feste Hoehe statt 1fr: in einem scrollenden Container loest 1fr gegen
       das SICHTBARE Fenster auf - jede Quartalsreihe wurde dann so hoch wie
       der ganze Reiter (gemessen 17 Zeilen fuer vier Textzeilen). 7 = zwei
       Rahmenzeilen plus die fuenf Zeilen einer vollen Kachel (Monat, Balken,
       Stunden, Tage, manueller Anteil). */
    YearPanel QuarterRow {
        height: 7;
    }

    /* 1fr, nicht auto - und overflow-y ist NICHT optional: passen die vier
       Quartalsreihen nicht in den Reiter, legt Textual sie ohne den
       Scroll-Container uebereinander (gemessen: alle vier melden dieselbe
       Hoehe UND dieselbe Position). So behalten sie ihre Hoehe, und man
       blaettert stattdessen. */
    YearPanel #year-grid {
        height: 1fr;
        overflow-y: auto;
    }

    /* Unten angedockt, damit Jahressumme und Forecast IMMER zu sehen sind.
       Der Reiter hat deutlich weniger Platz als das fruehere Modal (das nahm
       90 % des Bildschirms): bei 50 Terminalzeilen bleiben ihm 26. Ohne das
       Andocken laegen genau die Zahlen unter der Kante, wegen derer man die
       Ansicht aufmacht - scrollen muessen dann die Kacheln. */
    YearPanel #year-summary {
        dock: bottom;
        height: auto;
        min-height: 2;
        margin-top: 1;
        padding: 0 1;
        background: $surface;
    }
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._year = date.today().year
        self._month_data: dict[int, dict[str, Any]] = {}
        self._max_yearly = 0.0
        self._hourly_rate = 0.0
        self._vat_rate = 19.0
        self._vacation_days = 30
        self._hours_per_day = 8.0
        self._federal_state = "SN"
        # Zensiert Geldbetraege fuer Screenshots (gekoppelt an a-Anonymisierung).
        self._anonymized = False
        self._mark_manual = True
        self._manual_color = DEFAULT_MANUAL_COLOR
        # Hinweistext statt Zahlen, solange nichts geladen ist.
        self._message = ""

    def compose(self) -> ComposeResult:
        """Baut Kachelraster und Summenzeile - alle Kacheln leer.

        Ohne Ueberschrift: als Modal brauchte die Ansicht eine, im Reiter steht
        das Jahr bereits in der Kennzahlen-Leiste und in der Summenzeile
        ("2026 Gesamt: ..."). Zwei Zeilen weniger, und im Reiter zaehlt jede.
        """
        with Vertical(id="year-grid"):
            for quarter in range(4):
                with QuarterRow():
                    yield Static(_QUARTER_NAMES[quarter], classes="quarter-label")
                    for offset in range(3):
                        month = quarter * 3 + offset + 1
                        yield MonthTile(month=month, year=self._year, id=f"month-tile-{month}")

        yield Static("", id="year-summary")

    def on_mount(self) -> None:
        """Zeichnet den aktuellen Stand, sobald die Kinder da sind."""
        self._apply()

    @property
    def year(self) -> int:
        """Das zuletzt gesetzte Jahr."""
        return self._year

    @property
    def total_hours(self) -> float:
        """Summe der gebuchten Stunden ueber alle Monate."""
        return sum(float(data.get("actual", 0.0)) for data in self._month_data.values())

    @property
    def total_manual(self) -> float:
        """Summe des manuell erfassten Anteils."""
        return sum(float(data.get("manual", 0.0)) for data in self._month_data.values())

    @property
    def total_days(self) -> int:
        """Summe der Tage mit Buchung."""
        return sum(int(data.get("working_days", 0)) for data in self._month_data.values())

    def set_year(
        self,
        year: int,
        month_data: dict[int, dict[str, Any]],
        max_yearly_hours: float = 1720.0,
        hourly_rate: float = 0.0,
        vat_rate: float = 19.0,
        vacation_days: int = 30,
        hours_per_day: float = 8.0,
        federal_state: str = "SN",
        mark_manual: bool = True,
        manual_color: str = DEFAULT_MANUAL_COLOR,
    ) -> None:
        """Traegt einen geladenen Jahrgang in die Ansicht ein."""
        self._year = year
        self._month_data = dict(month_data)
        self._max_yearly = max_yearly_hours
        self._hourly_rate = hourly_rate
        self._vat_rate = vat_rate
        self._vacation_days = vacation_days
        self._hours_per_day = hours_per_day
        self._federal_state = federal_state
        self._mark_manual = mark_manual
        self._manual_color = manual_color
        self._message = ""
        self._apply()

    def show_message(self, message: str) -> None:
        """Zeigt einen Hinweis statt der Jahressumme (z.B. fehlende Zugangsdaten)."""
        self._message = message
        self._apply()

    def set_anonymized(self, value: bool) -> None:
        """Schaltet die Zensur der Geldbetraege ein/aus (Screenshot-Modus)."""
        self._anonymized = value
        self._apply()

    def set_manual_marking(self, enabled: bool, color: str) -> None:
        """Uebernimmt die Markierungs-Einstellungen des manuellen Anteils."""
        self._mark_manual = enabled
        self._manual_color = color
        self._apply()

    def _apply(self) -> None:
        """Schreibt den aktuellen Zustand in Titel, Kacheln und Summe."""
        if not self.is_mounted:
            return
        for month in range(1, 13):
            data = self._month_data.get(month, {})
            self.query_one(f"#month-tile-{month}", MonthTile).update_data(
                year=self._year,
                actual_hours=data.get("actual", 0.0),
                target_hours=data.get("target", 0.0),
                working_days=data.get("working_days", 0),
                target_days=data.get("target_days", 0),
                manual_hours=data.get("manual", 0.0),
                mark_manual=self._mark_manual,
                manual_color=self._manual_color,
            )
        summary = self.query_one("#year-summary", Static)
        summary.update(Text(self._message, style="dim") if self._message else self._build_summary())

    def _build_summary(self) -> Text:
        """Erzeugt die Jahres-Zusammenfassung."""
        text = Text()

        total_actual = self.total_hours
        total_manual = self.total_manual
        total_days = self.total_days

        text.append(t("year.total", year=self._year), style="bold")
        text.append(f"{format_number(total_actual, 1)}h", style="bold")

        if self._max_yearly > 0:
            remaining = self._max_yearly - total_actual
            pct = total_actual / self._max_yearly * 100

            text.append(f" / {format_number(self._max_yearly, 0)}h", style="dim")

            bar_len = 20
            filled = min(int(pct / 100 * bar_len), bar_len)
            bar_style = "bold green" if pct < 80 else ("bold yellow" if pct < 95 else "bold red")
            text.append("  [", style="dim")
            text.append("█" * filled, style=bar_style)
            text.append("░" * (bar_len - filled), style="dim")
            text.append("]", style="dim")
            text.append(f" {pct:.1f}%", style=bar_style)

            text.append("  |  ", style="dim")
            if remaining > 0:
                text.append(t("year.remaining", hours=format_number(remaining, 1)), style="bold green")
            else:
                text.append(t("year.exceeded", hours=format_number(abs(remaining), 1)), style="bold red")

        text.append("  |  ", style="dim")
        text.append(t("year.workdays", days=total_days), style="dim")

        # Manueller Jahresanteil nur zeigen, wenn es welchen gibt.
        if total_manual > 0:
            text.append("  |  ", style="dim")
            manual_style = f"bold #{self._manual_color}" if self._mark_manual else "bold"
            text.append(t("summary.manual") + ": ", style="dim")
            text.append(f"{format_number(total_manual)}h", style=manual_style)

        if self._hourly_rate > 0:
            netto = total_actual * self._hourly_rate
            brutto = netto * (1.0 + self._vat_rate / 100.0)
            netto_str = REDACTED_MONEY if self._anonymized else format_eur(netto)
            brutto_str = REDACTED_MONEY if self._anonymized else format_eur(brutto)
            text.append("\n")
            text.append(f"  {t('year.net')}: {netto_str}", style="bold")
            text.append("  |  ", style="dim")
            text.append(f"{t('year.gross')}: {brutto_str}", style="bold")

        # Forecast
        text.append("\n")
        text.append(self._build_forecast())

        return text

    def _build_forecast(self) -> Text:
        """Berechnet den Jahres-Forecast."""
        text = Text()

        import holidays as _holidays

        h = _holidays.country_holidays("DE", subdiv=self._federal_state, years=self._year)

        from datetime import timedelta

        total_workdays_year = 0
        current = date(self._year, 1, 1)
        end = date(self._year, 12, 31)
        one_day = timedelta(days=1)
        while current <= end:
            if current.weekday() < 5 and current not in h:
                total_workdays_year += 1
            current += one_day

        available_days = total_workdays_year - self._vacation_days
        forecast_hours = available_days * self._hours_per_day

        text.append(f"{t('year.forecast_header')}\n", style="dim")
        text.append(t("year.forecast_workdays", year=self._year), style="dim")
        text.append(f"{total_workdays_year}", style="bold")
        text.append(t("year.forecast_vacation", days=self._vacation_days), style="dim")
        text.append("  = ", style="dim")
        text.append(f"{t('year.forecast_available', days=available_days)}\n", style="bold")

        text.append(t("year.forecast_hours_label"), style="dim")
        text.append(
            t("year.forecast_hours_calc", days=available_days, per_day=format_number(self._hours_per_day, 0)),
            style="dim",
        )
        text.append(f"{format_number(forecast_hours, 0)}h\n", style="bold")

        if self._hourly_rate > 0:
            forecast_netto = forecast_hours * self._hourly_rate
            forecast_brutto = forecast_netto * (1.0 + self._vat_rate / 100.0)
            fc_netto_str = REDACTED_MONEY if self._anonymized else format_eur(forecast_netto)
            fc_brutto_str = REDACTED_MONEY if self._anonymized else format_eur(forecast_brutto)
            text.append(t("year.forecast_revenue_label"), style="dim")
            text.append(f"{t('year.net')}: {fc_netto_str}", style="bold green")
            text.append("  |  ", style="dim")
            text.append(f"{t('year.gross')}: {fc_brutto_str}", style="bold green")

        return text
